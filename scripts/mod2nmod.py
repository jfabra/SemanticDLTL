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
Rewrite a ``.mod`` trace model with one line per trace.

    python scripts/mod2nmod.py <model>

reads ``<model>.mod`` and writes

* ``<model>.desc``: the header line of the model;
* ``<model>.nmod``: one line per trace, the first field being the trace id and
  the remaining ones the events, separated by commas::

      SI,ev_CRP&135343080
      SI,ev_CRP&135504000
      VHA,ev_ER_Registration&128970000

  becomes ::

      SI,ev_CRP&135343080,ev_CRP&135504000
      VHA,ev_ER_Registration&128970000
"""
import sys

ID_SEP = ','


def load_mod(path_root: str) -> list[str]:
    with open(path_root + '.mod') as f:
        return [line.strip() for line in f if line.strip()]


def generate_desc(lines: list[str], path_root: str) -> None:
    with open(path_root + '.desc', 'w') as f:
        f.write(lines[0] + '\n')


def generate_nmod(lines: list[str], path_root: str) -> None:
    traces: dict[str, list[str]] = {}
    for line in lines[1:]:
        trace_id, _, event = line.partition(ID_SEP)
        traces.setdefault(trace_id, []).append(event)
    with open(path_root + '.nmod', 'w') as f:
        for trace_id, events in traces.items():
            f.write(ID_SEP.join([trace_id, *events]) + '\n')


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <model>   (reads <model>.mod)", file=sys.stderr)
        return 2
    lines = load_mod(argv[1])
    generate_desc(lines, argv[1])
    generate_nmod(lines, argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
