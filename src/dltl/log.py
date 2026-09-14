# -----------------------------------------------------------------------------
# SemanticDLTL: a DLTL model checker over finite traces
#
# Copyright (C) 2024-2026
#   Joaquín Ezpeleta, Universidad de Zaragoza, Spain
#   Javier Fabra, Universidad de Zaragoza, Spain
#   María José Ibáñez, Universidad de La Rioja, Spain
# Contact: semanticdltl@unizar.es
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of SemanticDLTL. It is free software: you can redistribute
# it and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version. See the LICENSE file for details.
#
# Based on: J. M. Couvreur, J. Ezpeleta, "A Linear Temporal Logic Model
# Checking Method over Finite Words with Correlated Transition Attributes",
# SIMPDA 2017, LNBIP vol. 340, Springer, 2019.
# -----------------------------------------------------------------------------
"""
Trace models: loading of ``.mod`` files and writing of checking results.

A ``.mod`` file has one header line describing the attributes, followed by one
event per line::

    aE,nV,@att,$p
    id1,a&1&a;1&a=1;b=2
    id1,b&1&a;2&a=1;b=2
    ...

The first character of each header field is the attribute type:

    'a'  atomic proposition        's'  string
    'n'  number (stored as float)  'b'  boolean
    '@'  set of strings ("v1;v2")  '$'  dictionary ("k1=v1;k2=v2")

Each event is stored as a tuple: position ``I_POS`` (0) holds the position of
the event in its trace (starting at 1), position ``I_ATOM`` (1) holds the
*frozenset* of atomic propositions of the event, and the following positions
hold the values of the non-atomic attributes, in header order.
``Log.column_index`` maps each non-atomic attribute name to its position in
that tuple, so that inside a data expression ``x[V]`` reads attribute ``V`` of
the event frozen in ``x``.

Values are shared between the events that spell them identically (the set of
atoms, a string, a float, the ``@`` frozenset or the ``$`` dictionary of one
event may be the very same object in a million others): a log is a few
hundred bytes per event instead of more than a kilobyte, and it loads faster.
Attribute values must therefore be treated as immutable by user propositions.
"""
from __future__ import annotations

import gc
import gzip
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ID_SEP = ','
ATRIB_SEP = '&'
VALS_SEP = ';'
SUF_MOD = '.mod'
SUF_GZ = '.gz'

# layout of the event tuple
I_POS = 0            # position of the event in its trace (1-based)
I_ATOM = 1           # set of atomic propositions of the event
FIRST_ATTR_INDEX = 2 # first non-atomic attribute

ATTRIBUTE_TYPES = frozenset({'a', 'n', 'b', 's', '@', '$'})

Event = tuple[Any, ...]
Trace = tuple[Event, ...]


# ---------------------------------------------------------------------------
# value casting

def cast_format(value_str: str, format: str) -> bool | float | str:
    """Cast ``value_str`` according to the declared attribute type ('n', 'b' or 's')."""
    val = value_str.strip()
    if format == 'n':
        if val == '':
            return 0
        try:
            return float(val)
        except ValueError:
            print(f"Warning: '{val}' is not a number, using 0.0", file=sys.stderr)
            return 0.0
    if format == 'b':
        if val.lower() == 'true':
            return True
        if val not in ('', 'false', 'False', 'FALSE'):
            print(f"Warning: '{val}' is not a boolean, using False", file=sys.stderr)
        return False
    return val  # 's'


def cast(value_str: str) -> bool | float | str:
    """Cast ``value_str`` depending on its content: bool, float or string."""
    val = value_str.strip()
    lowered = val.lower()
    if lowered == 'true':
        return True
    if lowered == 'false':
        return False
    try:
        return float(val)
    except ValueError:
        return val


# ---------------------------------------------------------------------------
# header / event parsing

def _parse_header(head: str) -> tuple[list[str], tuple[str, ...], tuple[str, ...], dict[str, int]]:
    """``"aE,nV,@att,$p"`` -> (attrib_desc, formats, field_names, column_index).

    Non-atomic attributes get consecutive positions starting at
    ``FIRST_ATTR_INDEX`` (positions ``I_POS`` and ``I_ATOM`` of the event tuple
    hold the event position and the set of atomic propositions).
    """
    attrib_desc = head.split(ID_SEP)
    formats = tuple(f[0] for f in attrib_desc)
    field_names = tuple(f[1:] for f in attrib_desc)
    for f in formats:
        if f not in ATTRIBUTE_TYPES:
            raise ValueError(f"Unknown attribute type '{f}' in header '{head}'")
    column_index: dict[str, int] = {}
    for fmt, name in zip(formats, field_names, strict=True):
        if fmt != 'a':
            column_index[name] = len(column_index) + FIRST_ATTR_INDEX
    return attrib_desc, formats, field_names, column_index


# Distinct raw values remembered per column. Categorical columns (atoms, user
# ids, sites, the emotion scores that are mostly 0.0) fit entirely and their
# values are shared by every event; a column of unique values (a timestamp)
# fills its cache once and is then parsed as before.
_VALUE_CACHE_LIMIT = 65536


def _parse_value(fmt: str, raw: str, line_no: int) -> Any:
    """Value of a non-atomic attribute of type ``fmt`` from its raw text."""
    if fmt == '@':
        return frozenset(v.strip() for v in raw.split(VALS_SEP))
    if fmt == '$':
        d: dict[str, Any] = {}
        for pair in raw.split(VALS_SEP):
            key, sep, value = pair.partition('=')
            if not sep:
                print(f"Error processing dictionary attribute values, line {line_no}: "
                      f"'{pair}'", file=sys.stderr)
                continue
            d[key.strip()] = cast(value)
        return d
    return cast_format(raw, fmt)  # 'n', 'b', 's'


class _EventBuilder:
    """Builds the event tuples of one model, sharing the values already seen.

    One cache per column maps the raw text of a value to the parsed value
    (bounded by ``_VALUE_CACHE_LIMIT``); the atom columns share one cache
    keyed by their raw texts, so identical sets of atoms are one frozenset.
    ``atomics`` collects every atomic proposition of the model.
    """

    def __init__(self, formats: tuple[str, ...]):
        self.formats = formats
        self.atom_columns = tuple(i for i, fmt in enumerate(formats) if fmt == 'a')
        self.attr_columns = tuple(i for i, fmt in enumerate(formats) if fmt != 'a')
        self.caches: dict[int, dict[str, Any]] = {i: {} for i in self.attr_columns}
        self.atom_cache: dict[Any, frozenset[str]] = {}
        self.atomics: set[str] = set()

    def event(self, values: list[str], line_no: int, position: int) -> Event:
        """Event tuple from the raw attribute values of one line (``position`` is 1-based)."""
        if len(values) != len(self.formats):
            raise ValueError(f"line {line_no}: expected {len(self.formats)} attribute values, "
                             f"got {len(values)}")
        atom_columns = self.atom_columns
        key = values[atom_columns[0]] if len(atom_columns) == 1 else \
            tuple(values[i] for i in atom_columns)
        atoms = self.atom_cache.get(key)
        if atoms is None:
            atoms = frozenset(values[i].strip() for i in atom_columns)
            self.atomics |= atoms
            if len(self.atom_cache) < _VALUE_CACHE_LIMIT:
                self.atom_cache[key] = atoms
        event = [position, atoms]
        for i in self.attr_columns:
            raw = values[i]
            cache = self.caches[i]
            value = cache.get(raw, cache)  # the cache itself marks a miss (None is a value)
            if value is cache:
                value = _parse_value(self.formats[i], raw, line_no)
                if len(cache) < _VALUE_CACHE_LIMIT:
                    cache[raw] = value
            event.append(value)
        return tuple(event)


# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Log:
    """A loaded trace model."""

    path: str                            # path of the .mod file, without the suffix
    traces: dict[str, Trace]             # trace id -> tuple of events
    sorted_ids: list[str]
    atomics: frozenset[str]              # every atomic proposition in the log
    column_index: dict[str, int]         # non-atomic attribute name -> position in the event
    attrib_desc: list[str]               # header fields, e.g. ['aE', 'nV', '@att', '$p']
    formats: tuple[str, ...]
    field_names: tuple[str, ...]

    # --- loading -----------------------------------------------------------
    @classmethod
    def load(cls, path: str) -> Log:
        """Load a model from ``<path>.mod`` or from a compressed ``<path>.mod.gz``.

        ``path`` may be given with or without the suffix. Result files are
        written next to the model, under ``<path>`` without suffixes.
        """
        path = str(path)
        compressed = path.endswith(SUF_MOD + SUF_GZ)
        if compressed:
            root = path[:-len(SUF_MOD + SUF_GZ)]
        else:
            root = path[:-len(SUF_MOD)] if path.endswith(SUF_MOD) else path
            compressed = (not Path(root + SUF_MOD).exists()
                          and Path(root + SUF_MOD + SUF_GZ).exists())
        opener = gzip.open if compressed else open
        traces: dict[str, list[Event]] = {}
        # the loop allocates millions of long-lived containers: the cyclic
        # garbage collector would traverse them all again and again for nothing
        gc_was_enabled = gc.isenabled()
        gc.disable()
        try:
            with opener(root + SUF_MOD + (SUF_GZ if compressed else ''), 'rt') as f:
                attrib_desc, formats, field_names, column_index = _parse_header(
                    f.readline().strip())
                builder = _EventBuilder(formats)
                current_id, trace = None, []
                for line_no, line in enumerate(f, start=2):
                    line = line.strip()
                    if not line:
                        continue
                    trace_id, _, rest = line.partition(ID_SEP)
                    if trace_id != current_id:  # the events of a trace are usually contiguous
                        current_id = trace_id
                        trace = traces.setdefault(trace_id, [])
                    trace.append(builder.event(rest.split(ATRIB_SEP), line_no, len(trace) + 1))
        finally:
            if gc_was_enabled:
                gc.enable()
        sorted_ids = sorted(traces)
        log = cls(path=root,
                  traces={tid: tuple(traces[tid]) for tid in sorted_ids},
                  sorted_ids=sorted_ids,
                  atomics=frozenset(builder.atomics),
                  column_index=column_index,
                  attrib_desc=attrib_desc,
                  formats=formats,
                  field_names=field_names)
        # the model lives for the whole session: keep the collector from
        # traversing it during the checks
        gc.freeze()
        return log

    # --- derived data ------------------------------------------------------
    @property
    def n_traces(self) -> int:
        return len(self.traces)

    @property
    def n_events(self) -> int:
        return sum(len(t) for t in self.traces.values())

    @property
    def trace_lengths(self) -> dict[str, int]:
        return {tid: len(self.traces[tid]) for tid in self.sorted_ids}

    def info(self) -> str:
        sep = "----------------------------------------"
        return "\n".join([sep,
                          f"file:      {self.path}{SUF_MOD}",
                          f"#traces:   {self.n_traces}",
                          f"#events:   {self.n_events}",
                          f"#atomics:  {len(self.atomics)}",
                          f"att. desc: {self.attrib_desc}",
                          sep])

    # --- output files ------------------------------------------------------
    def save_trace_lengths(self, path: str | None = None) -> str:
        """Write ``<id>,<length>`` per trace to ``<path>`` (default ``<log>_trace_lengths.csv``)."""
        path = path or self.path + '_trace_lengths.csv'
        with open(path, "w") as f:
            for tid in self.sorted_ids:
                f.write(f"{tid},{len(self.traces[tid])}\n")
        return path

    def save_results(self, results: dict[str, str], counts: dict[str, str],
                     checked_forms: list[str]) -> None:
        """Write ``<log>.res`` (1/0 per trace and formula), ``<log>.norm`` (ratio of
        events where the formula holds) and ``<log>.forms`` (the checked formulas)."""
        with open(self.path + '.res', "w") as f_res, open(self.path + '.norm', "w") as f_norm:
            for tid in self.sorted_ids:
                f_res.write(f"{results[tid]}\n")
                f_norm.write(f"{counts[tid]}\n")
        with open(self.path + '.forms', "w") as f_forms:
            for form in checked_forms:
                f_forms.write(f"{form}\n")

    # --- exploring results -------------------------------------------------
    def who(self, results: dict[str, str]) -> str:
        """Ids of the traces satisfying the last checked formula."""
        return self._what(results, '1')

    def who_not(self, results: dict[str, str]) -> str:
        """Ids of the traces not satisfying the last checked formula."""
        return self._what(results, '0')

    def _what(self, results: dict[str, str], val: str) -> str:
        return "".join(tid + " " for tid in self.sorted_ids
                       if results[tid].rpartition(',')[-1] == val)
