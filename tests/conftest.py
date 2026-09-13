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
"""Shared fixtures for the SemanticDLTL test-suite."""
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "examples"
GOLDEN = Path(__file__).resolve().parent / "golden"

RESULT_LINE_FIELDS = 3  # yes,no,pct  (the 4th field is the elapsed time)


@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    """Copy the sample example into a temporary directory.

    Returns the directory; the model is ``<dir>/sample.mod``. Result files
    written by the checker land in the same directory and never touch the repo.
    """
    for name in ("sample.mod", "sample.init", "formulas.txt", "sample2.mod", "formulas2.txt"):
        shutil.copy(EXAMPLES / name, tmp_path / name)
    return tmp_path


def result_lines(stdout: str) -> list[str]:
    """Extract ``yes,no,pct`` from each ``yes,no,pct,time`` line of a session output."""
    lines = []
    for line in stdout.splitlines():
        parts = line.strip().split(",")
        if len(parts) == 4 and all(_is_number(p) for p in parts):
            lines.append(",".join(parts[:RESULT_LINE_FIELDS]))
    return lines


def _is_number(s: str) -> bool:
    try:
        float(s)
    except ValueError:
        return False
    return True


def golden(name: str) -> str:
    return (GOLDEN / name).read_text()
