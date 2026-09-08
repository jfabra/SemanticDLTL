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
"""Same scenario as the CLI regression test, but through the library API."""
import io
from pathlib import Path

from conftest import golden, result_lines
from dltl import Log, Session
from dltl.cli import read_file


def test_session_matches_golden(sample_dir: Path):
    out = io.StringIO()
    session = Session(Log.load(sample_dir / "sample"), out=out)
    assert session.run(read_file(sample_dir / "sample.init"))
    assert not session.run(read_file(sample_dir / "formulas.txt"))  # ends with _AGUR
    assert result_lines(out.getvalue()) == golden("sample.stdout").split()
    for suffix in (".res", ".norm", ".forms"):
        assert (sample_dir / f"sample{suffix}").read_text() == golden(f"sample{suffix}")


def test_commands(sample_dir: Path, capsys):
    out = io.StringIO()
    session = Session(Log.load(sample_dir / "sample"), out=out)
    session.execute("_INFO")
    assert "#traces:   3" in out.getvalue()
    session.execute("_SET ?v 4, 2")
    assert session.macros["?v"] == ("4", "2")
    session.execute("_RE ?ab [ab]")
    assert session.macros["?ab"] == ("a", "b")
    session.execute("_RANGE ?r 1,5,2")
    assert session.macros["?r"] == ("1", "3", "5")
    summaries = session.check_formula('F x.("(x)x[V] == ?v")')
    assert [s.formula for s in summaries] == ['F x.("(x)x[V] == 4")', 'F x.("(x)x[V] == 2")']
    assert [(s.yes, s.no) for s in summaries] == [(2, 1), (1, 2)]
    session.execute("_WHO")
    session.execute("_WHO_NOT")
    assert out.getvalue().splitlines()[-2:] == ["id2 ", "id0 id1 "]
    session.execute("_CLEAR_DATA")
    assert session.checked_forms == [] and session.results["id0"] == "id0"
    session.execute("_WRITE_LENGTHS")
    assert (sample_dir / "sample_trace_lengths.txt").exists()
    assert session.execute("_AGUR") is False


def test_bad_macro_name_and_bad_formula_do_not_break_the_session(sample_dir: Path, capsys):
    session = Session(Log.load(sample_dir / "sample"), out=io.StringIO())
    session.execute("_SET v 1,2")
    assert session.macros == {}
    session.execute("F (a")
    assert session.checked_forms == []
    err = capsys.readouterr().err
    assert "macro name" in err and "Syntax error" in err
    assert session.execute("a") is True
    assert session.checked_forms == ["a"]
