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
"""Every Python source file carries the SemanticDLTL copyright/license header."""
from pathlib import Path

from conftest import REPO_ROOT

HEADER_LINES = (
    "# SemanticDLTL: a DLTL model checker over finite traces",
    "# SPDX-License-Identifier: GPL-3.0-or-later",
)


def python_sources() -> list[Path]:
    files = [REPO_ROOT / "MC.py"]
    for sub in ("src/dltl", "tests", "examples"):
        files += sorted((REPO_ROOT / sub).glob("*.py"))
    return files


def test_every_source_file_has_the_header():
    missing = []
    for f in python_sources():
        head = f.read_text().splitlines()[:25]
        if not all(line in head for line in HEADER_LINES):
            missing.append(f.relative_to(REPO_ROOT))
    assert not missing, f"files without header: {missing}"


def test_header_comes_before_the_docstring():
    for f in python_sources():
        text = f.read_text()
        if '"""' in text:
            assert text.index("SPDX-License-Identifier") < text.index('"""'), f
