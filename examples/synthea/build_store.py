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
Load the knowledge graph of a log (``log_*.nq`` or ``log_*.nq.gz``) into an
Oxigraph store, so that the propositions of ``propositions.py`` can query it.

    python build_store.py logs/log_50_6_20.nq            # -> ./store
    python build_store.py logs/log_500_21_40.nq.gz  mystore --replace

Requires ``pyoxigraph`` (``pip install "semanticdltl[synthea]"``).
"""
from __future__ import annotations

import argparse
import gzip
import shutil
import sys
from pathlib import Path


def build_store(nq_path: str | Path, store_dir: str | Path, replace: bool = False) -> int:
    """Create the store at ``store_dir`` from ``nq_path``; returns the number of quads."""
    from pyoxigraph import RdfFormat, Store

    store_dir = Path(store_dir)
    if store_dir.exists() and any(store_dir.iterdir()):
        if not replace:
            raise FileExistsError(f"'{store_dir}' already exists; use --replace to overwrite it")
        shutil.rmtree(store_dir)
    nq_path = Path(nq_path)
    opener = gzip.open if nq_path.suffix == ".gz" else open
    store = Store(str(store_dir))
    with opener(nq_path, "rb") as f:
        store.bulk_load(f, RdfFormat.N_QUADS)
    return len(store)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("nq", help="N-Quads file, optionally gzipped")
    default_store = str(Path(__file__).resolve().parent / "store")
    parser.add_argument("store", nargs="?", default=default_store,
                        help="directory of the Oxigraph store (default: store/ next to the script)")
    parser.add_argument("--replace", action="store_true", help="overwrite an existing store")
    args = parser.parse_args(argv)
    try:
        n = build_store(args.nq, args.store, args.replace)
    except (OSError, ImportError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(f"{n} quads loaded into {args.store}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
