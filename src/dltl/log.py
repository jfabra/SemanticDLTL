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
Trace models: loading of ``.mod`` files (and, through :mod:`dltl.xes`, of XES
event logs) and writing of checking results.

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
the event in its trace (starting at 1), position ``I_ATOM`` (1) holds the *set*
of atomic propositions of the event, and the following positions hold the
values of the non-atomic attributes, in header order. ``Log.column_index``
maps each non-atomic attribute name to its position in that tuple, so that
inside a data expression ``x[V]`` reads attribute ``V`` of the event frozen
in ``x``.

An XES event log (``.xes`` or ``.xes.gz``) is not parsed here: ``Log.load``
hands it to :func:`dltl.xes.load_xes`, which produces the header fields and
the raw values a ``.mod`` file would contain and builds the model with
``Log.from_rows``, the same constructor used for ``.mod`` files.
"""
from __future__ import annotations

import gzip
import os
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ID_SEP = ','
ATRIB_SEP = '&'
VALS_SEP = ';'
SUF_MOD = '.mod'
SUF_XES = '.xes'
SUF_GZ = '.gz'

# layout of the event tuple
I_POS = 0            # position of the event in its trace (1-based)
I_ATOM = 1           # set of atomic propositions of the event
FIRST_ATTR_INDEX = 2 # first non-atomic attribute

ATTRIBUTE_TYPES = frozenset({'a', 'n', 'b', 's', '@', '$'})

Event = tuple[Any, ...]
Trace = tuple[Event, ...]
Row = tuple[int, str, list[str]]  # line number, trace id, raw attribute values


def xes_root(path: str | os.PathLike) -> str | None:
    """``path`` without its ``.xes`` or ``.xes.gz`` suffix; ``None`` if it is not an XES file."""
    path = str(path)
    for suffix in (SUF_XES + SUF_GZ, SUF_XES):
        if path.lower().endswith(suffix):
            return path[:-len(suffix)]
    return None


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
    if val.lower() == 'true':
        return True
    if val.lower() == 'false':
        return False
    try:
        return float(val)
    except ValueError:
        return val


# ---------------------------------------------------------------------------
# header / event parsing

def _parse_header(attrib_desc: list[str]) -> tuple[tuple[str, ...], tuple[str, ...],
                                                   dict[str, int]]:
    """``['aE', 'nV', '@att', '$p']`` -> (formats, field_names, column_index).

    Non-atomic attributes get consecutive positions starting at
    ``FIRST_ATTR_INDEX`` (positions ``I_POS`` and ``I_ATOM`` of the event tuple
    hold the event position and the set of atomic propositions).
    """
    formats = tuple(f[:1] for f in attrib_desc)
    field_names = tuple(f[1:] for f in attrib_desc)
    for f in formats:
        if f not in ATTRIBUTE_TYPES:
            raise ValueError(f"Unknown attribute type '{f}' in header "
                             f"'{ID_SEP.join(attrib_desc)}'")
    column_index: dict[str, int] = {}
    for fmt, name in zip(formats, field_names, strict=True):
        if fmt != 'a':
            column_index[name] = len(column_index) + FIRST_ATTR_INDEX
    return formats, field_names, column_index


def _mod_rows(lines: Iterable[str]) -> Iterator[Row]:
    """The events of a ``.mod`` file, from the lines that follow its header."""
    for line_no, line in enumerate(lines, start=2):
        line = line.strip()
        if line:
            trace_id, _, rest = line.partition(ID_SEP)
            yield line_no, trace_id, rest.split(ATRIB_SEP)


def _make_event(formats: tuple[str, ...], field_names: tuple[str, ...], values: list[str],
                column_index: dict[str, int], line_no: int, position: int) -> Event:
    """Build the event tuple from the raw attribute values of one line.

    ``position`` is the 1-based position of the event in its trace.
    """
    if len(values) != len(formats):
        raise ValueError(f"line {line_no}: expected {len(formats)} attribute values, "
                         f"got {len(values)}")
    event: list[Any] = [position, set()] + [None] * len(column_index)
    for fmt, name, raw in zip(formats, field_names, values, strict=True):
        if fmt == 'a':
            event[I_ATOM].add(raw.strip())
        elif fmt == '@':
            event[column_index[name]] = {v.strip() for v in raw.split(VALS_SEP)}
        elif fmt == '$':
            d: dict[str, Any] = {}
            # an empty value is an empty dictionary, not a malformed pair
            for pair in raw.split(VALS_SEP) if raw.strip() else ():
                key, sep, value = pair.partition('=')
                if not sep:
                    print(f"Error processing dictionary attribute values, line {line_no}: "
                          f"'{pair}'", file=sys.stderr)
                    continue
                d[key.strip()] = cast(value)
            event[column_index[name]] = d
        else:  # 'n', 'b', 's'
            event[column_index[name]] = cast_format(raw, fmt)
    return tuple(event)


# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Log:
    """A loaded trace model."""

    path: str                            # path of the model file, without the suffix
    traces: dict[str, Trace]             # trace id -> tuple of events
    sorted_ids: list[str]
    atomics: frozenset[str]              # every atomic proposition in the log
    column_index: dict[str, int]         # non-atomic attribute name -> position in the event
    attrib_desc: list[str]               # header fields, e.g. ['aE', 'nV', '@att', '$p']
    formats: tuple[str, ...]
    field_names: tuple[str, ...]
    source: str = ''                     # file the model was read from; '' means <path>.mod

    # --- loading -----------------------------------------------------------
    @classmethod
    def from_rows(cls, path: str, attrib_desc: Iterable[str], rows: Iterable[Row],
                  source: str = '') -> Log:
        """Build a model from its header fields and the raw values of its events.

        ``attrib_desc`` is the header (``['aE', 'nV', '@att', '$p']``) and each
        row is ``(line_no, trace_id, values)``, where ``values`` holds one raw
        string per header field, written as in a ``.mod`` file, and ``line_no``
        is only used in error messages. Events are appended to their trace in
        the order of the rows.
        """
        attrib_desc = list(attrib_desc)
        formats, field_names, column_index = _parse_header(attrib_desc)
        traces: dict[str, list[Event]] = {}
        atomics: set[str] = set()
        for line_no, trace_id, values in rows:
            trace = traces.setdefault(trace_id, [])
            event = _make_event(formats, field_names, values, column_index,
                                line_no, position=len(trace) + 1)
            atomics |= event[I_ATOM]
            trace.append(event)
        sorted_ids = sorted(traces)
        return cls(path=path,
                   traces={tid: tuple(traces[tid]) for tid in sorted_ids},
                   sorted_ids=sorted_ids,
                   atomics=frozenset(atomics),
                   column_index=column_index,
                   attrib_desc=attrib_desc,
                   formats=formats,
                   field_names=field_names,
                   source=source)

    @classmethod
    def load(cls, path: str) -> Log:
        """Load a model from ``<path>.mod`` or from a compressed ``<path>.mod.gz``.

        ``path`` may be given with or without the suffix. Result files are
        written next to the model, under ``<path>`` without suffixes.

        A path ending in ``.xes`` or ``.xes.gz`` is read as an XES event log
        with the default options of :func:`dltl.xes.load_xes`; call that
        function to give a mapping schema or other options.
        """
        path = str(path)
        if xes_root(path) is not None:
            from dltl.xes import load_xes  # lazy: dltl.xes imports this module
            return load_xes(path)
        compressed = path.endswith(SUF_MOD + SUF_GZ)
        if compressed:
            root = path[:-len(SUF_MOD + SUF_GZ)]
        else:
            root = path[:-len(SUF_MOD)] if path.endswith(SUF_MOD) else path
            compressed = (not Path(root + SUF_MOD).exists()
                          and Path(root + SUF_MOD + SUF_GZ).exists())
        opener = gzip.open if compressed else open
        with opener(root + SUF_MOD + (SUF_GZ if compressed else ''), 'rt') as f:
            attrib_desc = f.readline().strip().split(ID_SEP)
            return cls.from_rows(root, attrib_desc, _mod_rows(f))

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
                          f"file:      {self.source or self.path + SUF_MOD}",
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
