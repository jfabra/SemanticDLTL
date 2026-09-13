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
"""The semantic example of examples/synthea: skipped when pyoxigraph is not installed."""
import importlib.util
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, golden, result_lines
from dltl import Log, Session
from dltl.cli import read_file

pytest.importorskip("pyoxigraph")

SYNTHEA = REPO_ROOT / "examples" / "synthea"
LOG = "log_50_6_20"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def store(tmp_path_factory) -> Path:
    """A fresh Oxigraph store built from the small log.

    One per test: Oxigraph locks a store directory for a single process, and
    the CLI test opens its store from a subprocess.
    """
    store_dir = tmp_path_factory.mktemp("store")
    builder = load_module("build_store", SYNTHEA / "build_store.py")
    assert builder.build_store(SYNTHEA / "logs" / f"{LOG}.nq", store_dir, replace=True) > 2000
    return store_dir


def test_session_matches_golden(store: Path, tmp_path: Path):
    props = load_module("synthea_props", SYNTHEA / "propositions.py")
    props.set_store(store)
    shutil.copy(SYNTHEA / "logs" / f"{LOG}.mod", tmp_path / f"{LOG}.mod")
    out = io.StringIO()
    session = Session(Log.load(tmp_path / LOG), props, out=out)
    assert session.run(read_file(SYNTHEA / "formulas.txt"))
    assert result_lines(out.getvalue()) == golden("synthea.stdout").split()


def test_cli_with_store_from_environment(store: Path, tmp_path: Path):
    shutil.copy(SYNTHEA / "logs" / f"{LOG}.mod", tmp_path / f"{LOG}.mod")
    cmd = [sys.executable, str(REPO_ROOT / "MC.py"), "--log-file", str(tmp_path / LOG),
           "--propositions", str(SYNTHEA / "propositions.py"),
           "--formula-file", str(SYNTHEA / "formulas.txt"), "--no-interactive"]
    env = {**os.environ, "SYNTHEA_STORE": str(store)}
    proc = subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True, timeout=300,
                          env=env, check=False)
    assert proc.returncode == 0, proc.stderr
    assert result_lines(proc.stdout) == golden("synthea.stdout").split()


def test_propositions_query_the_graph_of_the_event(store: Path):
    props = load_module("synthea_props2", SYNTHEA / "propositions.py")
    props.set_store(store)
    with_test = "<http://example.org/event/allergies_trace_1_L7>"
    assert props.has_code(with_test, 395142003) == props.Allergy_screening_test(with_test)
    first = "<http://example.org/event/allergies_trace_1_L1>"
    assert props.has_state_type(first, "Initial") and not props.has_code(first, 395142003)
    assert props.same_code(first, first) is False  # the initial state has no clinical code


def test_generator_is_reproducible_and_loads(tmp_path: Path):
    gen = load_module("generate_logs", SYNTHEA / "generate_logs.py")
    args = ["--traces", "1", "--min-steps", "6", "--max-steps", "20", "--seed", "7",
            "--base-time", "1700000000"]
    assert gen.main([*args, "--out-dir", str(tmp_path / "a")]) == 0
    assert gen.main([*args, "--out-dir", str(tmp_path / "b")]) == 0
    mod_a, mod_b = tmp_path / "a" / "log_10_6_20.mod", tmp_path / "b" / "log_10_6_20.mod"
    assert mod_a.read_bytes() == mod_b.read_bytes()
    assert (tmp_path / "a" / "log_10_6_20.nq").read_bytes() == \
        (tmp_path / "b" / "log_10_6_20.nq").read_bytes()
    log = Log.load(mod_a)
    assert log.n_traces == 10  # ten disease modules, submodules are not simulated on their own
    assert log.field_names == ("Activity", "Timestamp", "Actor", "ActionType", "Snomed", "Event",
                               "Workflow")
    # the length limit is drawn from [6, 20]; a trace ends earlier when its module terminates
    assert all(1 <= n <= 20 for n in log.trace_lengths.values())
