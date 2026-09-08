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
Convert a CSV event log into a ``.mod`` trace model.

    python scripts/csv2mod.py <log>

reads ``<log>.csv`` with the columns

    CaseID,Activity,Timestamp,Actor,ActionType,ModelReference,Details

writes ``<log>_cleaned.csv`` (activities and action types turned into valid
atomic propositions) and ``<log>.mod`` with the header

    aActivity,nTimestamp,aActor,aActionType,sModelReference,$Details

Requires pandas (``pip install semanticdltl[scripts]``).
"""
import sys

import pandas as pd

HEADER = "aActivity,nTimestamp,aActor,aActionType,sModelReference,$Details"


def load_log(path_root: str) -> pd.DataFrame:
    log = pd.read_csv(path_root + '.csv')
    # atomic propositions cannot contain spaces, dashes or slashes
    log['Activity'] = "ac_" + log['Activity'].str.replace(r'[ -/]', '_', regex=True)
    log['Actor'] = log['Actor'].str.replace(r'[ -/]', '_', regex=True)
    log['ActionType'] = "at_" + log['ActionType'].str.replace(r'[ -/]', '_', regex=True)
    log.to_csv(path_root + '_cleaned.csv', index=False)
    return log


def generate_mod(log: pd.DataFrame, path_root: str) -> None:
    with open(path_root + '.mod', 'w') as f:
        f.write(HEADER + '\n')
        for _, row in log.iterrows():
            f.write(str(row.iloc[0]) + ',' + '&'.join(row.iloc[1:].astype(str)) + '\n')


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <log>   (reads <log>.csv, writes <log>.mod)", file=sys.stderr)
        return 2
    generate_mod(load_log(argv[1]), argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
