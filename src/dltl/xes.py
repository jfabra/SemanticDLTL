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
Direct loading of XES event logs (eXtensible Event Stream, IEEE 1849).

``load_xes`` reads a ``.xes`` (or gzipped ``.xes.gz``) file into a
:class:`dltl.log.Log` without writing a ``.mod`` file. Every event is turned
into the raw field values that a ``.mod`` line would carry, and the model is
built from them with ``Log.from_rows``, the constructor used for ``.mod``
files, so that both formats share one definition of how raw values become
events and a model loaded from XES is one that a ``.mod`` file can express.

How the attributes of the events become attributes of the model is described
by an optional *mapping schema*, an XML file with one entry per attribute::

    <container key="mod:schema">
        <string key="concept:name"   value="aActivity"/>
        <string key="time:timestamp" value="nTimestamp"/>
        <string key="org:resource"   value="sResource"/>
    </container>

``key`` is the name of the attribute in the XES file; the first character of
``value`` is its type in the model (``a``, ``s``, ``n``, ``b``, ``@``, ``$``,
see :mod:`dltl.log`) and the rest its name. Without a schema, ``concept:name``
(the activity) is an atomic proposition. Attributes that the schema does not
mention keep their XES name and get a type from their XES type
(``DEFAULT_MOD_TYPE``), in the order in which they first appear in the log.

Conversion rules:

* a date becomes a number, the milliseconds since 1970-01-01 00:00:00 UTC;
* the value of an atomic attribute becomes an identifier: characters that
  cannot be part of one are replaced by ``_`` (``Hand washing`` is the atomic
  proposition ``Hand_washing``); trace identifiers are treated in the same way;
* in strings, and in the items of sets and dictionaries, the characters that
  are separators in a ``.mod`` file (``& , ; =``, tabs and line breaks) are
  replaced by ``_``;
* an attribute missing in an event gets ``_`` (atomic), ``''`` (string), ``0``
  (number), ``False`` (boolean) or an empty set or dictionary.
"""
from __future__ import annotations

import gzip
import math
import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from dltl.log import ATTRIBUTE_TYPES, SUF_GZ, Log, Row, xes_root

SCHEMA_KEY = "mod:schema"
DEFAULT_TRACE_ID_KEY = "concept:name"

XES_ATTRIBUTE_TAGS = frozenset({"string", "date", "int", "float", "boolean", "id",
                                "list", "container"})

# type given to the attributes that the schema does not mention
DEFAULT_MOD_TYPE = {
    "string": "s",
    "id": "a",
    "int": "n",
    "float": "n",
    "date": "n",
    "boolean": "b",
    "list": "@",
    "container": "$",
}

# raw value of an attribute missing in an event
_MISSING = {"a": "_", "s": "", "n": "0", "b": "False", "@": "", "$": ""}


@dataclass(frozen=True)
class Mapping:
    """XES attribute ``xes_name`` is attribute ``mod_name``, of type ``mod_type``, in the model."""
    xes_name: str
    mod_type: str
    mod_name: str

    @property
    def header(self) -> str:
        return self.mod_type + self.mod_name


@dataclass
class XesValue:
    xes_type: str
    value: Any


# schema used when none is given: the activity is an atomic proposition
DEFAULT_SCHEMA = (Mapping("concept:name", "a", "concept:name"),)


# ---------------------------------------------------------------------------
# value conversion

def local_name(tag: str) -> str:
    """Remove the XML namespace from a tag."""
    return tag.rsplit("}", 1)[-1]


def atomic_identifier(value: Any, fallback: str = "_") -> str:
    """Convert a value into a non-empty conventional identifier."""
    text = str(value).strip()
    text = re.sub(r"[^\w]", "_", text, flags=re.UNICODE)
    text = re.sub(r"_+", "_", text)
    if not text:
        text = fallback
    if text[0].isdigit():
        text = "_" + text
    return text


def safe_string(value: Any) -> str:
    """Replace the characters that are separators or line breaks in a ``.mod`` file."""
    return re.sub(r"[&,;=\r\n\t]", "_", str(value))


def timestamp_milliseconds(value: str) -> int:
    """Convert an ISO 8601 date to milliseconds since 1970-01-01 UTC."""
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"Invalid XES timestamp: {value!r}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return int(dt.timestamp() * 1000)


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().casefold()
    if text in {"true", "1"}:
        return True
    if text in {"false", "0"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def format_number(value: Any, attribute: str) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if not isinstance(value, float):
        try:
            value = float(str(value).strip())
        except ValueError as exc:
            raise ValueError(f"Unable to convert {attribute!r}={value!r} to a number") from exc
    if not math.isfinite(value):
        raise ValueError(f"Non-finite number for {attribute!r}")
    return format(value, ".15g")


def format_value(xes_value: XesValue | None, mapping: Mapping) -> str:
    """The raw value of an attribute of an event, as a ``.mod`` file would hold it."""
    if xes_value is None:
        return _MISSING[mapping.mod_type]
    value = xes_value.value
    if mapping.mod_type == "a":
        return atomic_identifier(value)
    if mapping.mod_type == "s":
        return safe_string(value)
    if mapping.mod_type == "n":
        return format_number(value, mapping.xes_name)
    if mapping.mod_type == "b":
        return "True" if parse_bool(value) else "False"
    if mapping.mod_type == "@":
        items = value if isinstance(value, list) else [value]
        return ";".join(safe_string(item) for item in items)
    # "$"
    if not isinstance(value, list) or any(not isinstance(item, tuple) for item in value):
        raise ValueError(f"{mapping.xes_name!r} is not an XES container")
    return ";".join(f"{safe_string(key)}={safe_string(item)}" for key, item in value)


# ---------------------------------------------------------------------------
# XES attributes

def parse_xes_attribute(element: ET.Element) -> tuple[str, XesValue]:
    """``<int key="k" value="3"/>`` -> ``('k', XesValue('int', 3))``."""
    tag = local_name(element.tag)
    key = element.get("key")
    if key is None:
        raise ValueError(f"XES attribute <{tag}> has no key")
    raw = element.get("value", "")

    if tag in {"string", "id"}:
        return key, XesValue(tag, raw)
    if tag == "date":
        return key, XesValue(tag, timestamp_milliseconds(raw))
    if tag == "int":
        try:
            return key, XesValue(tag, int(raw))
        except ValueError as exc:
            raise ValueError(f"Invalid integer in {key!r}: {raw!r}") from exc
    if tag == "float":
        try:
            number = float(raw)
        except ValueError as exc:
            raise ValueError(f"Invalid number in {key!r}: {raw!r}") from exc
        if not math.isfinite(number):
            raise ValueError(f"Non-finite number in {key!r}: {raw!r}")
        return key, XesValue(tag, number)
    if tag == "boolean":
        return key, XesValue(tag, parse_bool(raw))
    if tag == "list":
        items: list[Any] = []
        for child in element:
            candidates: Iterable[ET.Element]
            candidates = child if local_name(child.tag) == "values" else (child,)
            for item in candidates:
                _, parsed = parse_xes_attribute(item)
                if parsed.xes_type in {"list", "container"}:
                    raise ValueError(f"Nested collections are not supported in {key!r}")
                items.append(parsed.value)
        return key, XesValue(tag, items)
    if tag == "container":
        pairs: list[tuple[str, Any]] = []
        for child in element:
            child_key, parsed = parse_xes_attribute(child)
            if parsed.xes_type in {"list", "container"}:
                raise ValueError(f"Nested collections are not supported in {key!r}")
            pairs.append((child_key, parsed.value))
        return key, XesValue(tag, pairs)
    raise ValueError(f"Unsupported XES attribute type: <{tag}>")


def direct_attributes(parent: ET.Element) -> dict[str, XesValue]:
    """The attributes of a trace or event (its children that are XES attributes)."""
    result: dict[str, XesValue] = {}
    for child in parent:
        if local_name(child.tag) in XES_ATTRIBUTE_TAGS:
            key, value = parse_xes_attribute(child)
            result[key] = value
    return result


# ---------------------------------------------------------------------------
# mapping schema

def load_schema(schema_path: str | os.PathLike) -> list[Mapping]:
    """Read the ``mod:schema`` container of an XML file (its root or any element inside)."""
    try:
        root = ET.parse(schema_path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML schema '{schema_path}': {exc}") from exc

    container = next((element for element in root.iter()
                      if local_name(element.tag) == "container"
                      and element.get("key") == SCHEMA_KEY), None)
    if container is None:
        raise ValueError(f'<container key="{SCHEMA_KEY}"> not found in \'{schema_path}\'')

    mappings: list[Mapping] = []
    seen_xes: set[str] = set()
    for element in container:
        if local_name(element.tag) != "string":
            raise ValueError(f"Only <string> elements are allowed inside {SCHEMA_KEY}")
        xes_name = element.get("key")
        specification = element.get("value", "")
        if not xes_name:
            raise ValueError("Schema entry without an XES key")
        if len(specification) < 2 or specification[0] not in ATTRIBUTE_TYPES:
            raise ValueError(f"Invalid specification for {xes_name!r}: {specification!r} "
                             "(expected a type, one of 'a', 's', 'n', 'b', '@', '$', "
                             "followed by a name)")
        if xes_name in seen_xes:
            raise ValueError(f"Duplicate XES attribute in schema: {xes_name!r}")
        seen_xes.add(xes_name)
        mappings.append(Mapping(xes_name, specification[0], specification[1:]))

    if not mappings:
        raise ValueError(f"The {SCHEMA_KEY} container is empty")
    _check_names(mappings)
    return mappings


def _check_names(mappings: Iterable[Mapping]) -> None:
    """Two attributes of the model cannot share a name (nor two atomic ones a header)."""
    seen: set[tuple[bool, str]] = set()
    for mapping in mappings:
        key = (mapping.mod_type == "a", mapping.mod_name)
        if key in seen:
            raise ValueError(f"Duplicate attribute {mapping.header!r} (from XES attribute "
                             f"{mapping.xes_name!r}); rename one of them in the schema")
        seen.add(key)


# ---------------------------------------------------------------------------
# loading

def load_xes(path: str | os.PathLike, schema: str | os.PathLike | None = None,
             trace_id_key: str = DEFAULT_TRACE_ID_KEY, ignore: bool = False) -> Log:
    """Load the XES event log ``path`` (``.xes`` or gzipped ``.xes.gz``) as a model.

    ``schema`` is the XML file with the ``mod:schema`` mapping (see the module
    documentation); without it only ``concept:name`` is mapped, as an atomic
    proposition. The attributes of the events that the schema does not mention
    are added with a type derived from their XES type, unless ``ignore`` is
    true. ``trace_id_key`` is the trace attribute used as trace identifier; a
    trace without it is called ``trace_<n>``.

    Result files are written next to the log, under ``path`` without its
    suffix. Raises ``ValueError`` if the log or the schema is not valid.
    """
    path = str(path)
    root = xes_root(path)
    mappings = load_schema(schema) if schema is not None else list(DEFAULT_SCHEMA)
    known = {mapping.xes_name for mapping in mappings}

    # One pass over the file. The header is complete only at the end, since an
    # attribute may first appear in any event: the rows of earlier events are
    # shorter and are completed below with the value of a missing attribute.
    rows: list[Row] = []
    n_traces = 0
    opener = gzip.open if path.lower().endswith(SUF_GZ) else open
    try:
        with opener(path, "rb") as f:
            for _, trace in ET.iterparse(f, events=("end",)):
                if local_name(trace.tag) != "trace":
                    continue
                fallback = f"trace_{n_traces}"
                source = direct_attributes(trace).get(trace_id_key)
                trace_id = atomic_identifier(fallback if source is None else source.value,
                                             fallback=fallback)
                for event in trace:
                    if local_name(event.tag) != "event":
                        continue
                    attributes = direct_attributes(event)
                    if not ignore:
                        for name, xes_value in attributes.items():
                            if name not in known:
                                known.add(name)
                                mappings.append(
                                    Mapping(name, DEFAULT_MOD_TYPE[xes_value.xes_type], name))
                    rows.append((len(rows) + 1, trace_id,
                                 [format_value(attributes.get(mapping.xes_name), mapping)
                                  for mapping in mappings]))
                n_traces += 1
                trace.clear()
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XES file '{path}': {exc}") from exc

    _check_names(mappings)
    missing = [format_value(None, mapping) for mapping in mappings]
    return Log.from_rows(path if root is None else root,
                         [mapping.header for mapping in mappings],
                         ((n, trace_id, values + missing[len(values):])
                          for n, trace_id, values in rows),
                         source=path)
