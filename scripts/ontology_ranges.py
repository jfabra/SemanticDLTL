#!/usr/bin/env python3
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
Read the datatype properties of an OWL ontology and cast attribute values
according to their declared range.

    python scripts/ontology_ranges.py [ontology.owl]

Requires rdflib (``pip install semanticdltl[scripts]``).
"""
import sys
from datetime import date, datetime
from pathlib import Path

from rdflib import OWL, RDF, RDFS, Graph

DEFAULT_ONTOLOGY = Path(__file__).resolve().parent.parent / "examples/semantic/segitour.owl"


def property_ranges(ontology: str) -> dict[str, str]:
    g = Graph()
    g.parse(ontology, format="xml")
    ranges = {}
    for prop in g.subjects(RDF.type, OWL.DatatypeProperty):
        rng = g.value(prop, RDFS.range)
        if rng is not None:
            ranges[str(prop)] = str(rng)
    return ranges


def cast_value(ranges: dict[str, str], prop_uri: str, value_str: str) -> object:
    rng = ranges.get(prop_uri)
    if rng == "xsd:integer":
        return int(value_str)
    if rng == "xsd:boolean":
        val = value_str.lower()
        if val in ("true", "1"):
            return True
        if val in ("false", "0"):
            return False
        raise ValueError(f"invalid boolean value: {value_str}")
    if rng == "xsd:date":
        try:
            return datetime.strptime(value_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"invalid date: {value_str}, expected 'YYYY-MM-DD'") from None
    return value_str


def main(argv: list[str]) -> int:
    ontology = argv[1] if len(argv) > 1 else str(DEFAULT_ONTOLOGY)
    ranges = property_ranges(ontology)
    print("Datatype properties and ranges:")
    for k, v in ranges.items():
        print(f"{k} --> {v}")
    example = ("estur:resultCount", "6")
    value = cast_value(ranges, *example)
    print(f"\n{example[0]} = {example[1]!r} -> {value!r} ({type(value).__name__})")
    assert isinstance(value, (int, bool, date, str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
