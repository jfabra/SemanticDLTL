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
"""Backward-compatible entry point: ``python MC.py log-file=<model> ...``.

The implementation lives in the ``dltl`` package (``src/dltl``). Install it
with ``pip install -e .`` or run this file directly from the repository root.
"""
import os
import sys

try:
    from dltl.cli import main
except ImportError:  # running from a checkout without installing the package
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
    from dltl.cli import main

if __name__ == "__main__":
    sys.exit(main())
