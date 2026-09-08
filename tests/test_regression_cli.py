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
"""End-to-end regression: run the command-line tool on the sample example
and compare against the golden output captured from the original prototype."""
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT, golden, result_lines

MC_PY = REPO_ROOT / "MC.py"


def run_legacy(workdir: Path) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable, str(MC_PY),
        f"log-file={workdir / 'sample'}",
        f"init-file={workdir / 'sample.init'}",
        f"formula-file={workdir / 'formulas.txt'}",
        "interactive=false",
    ]
    return subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=60)


def test_legacy_invocation_matches_golden(sample_dir: Path):
    proc = run_legacy(sample_dir)
    assert proc.returncode == 0, proc.stderr
    assert result_lines(proc.stdout) == golden("sample.stdout").split()
    for suffix in (".res", ".norm", ".forms"):
        assert (sample_dir / f"sample{suffix}").read_text() == golden(f"sample{suffix}")
