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
import io

import pytest

from dltl.cli import build_parser, main, normalize_legacy_argv, read_lines


def test_normalize_legacy_argv():
    assert normalize_legacy_argv(["log-file=m", "init-file=i.txt", "formula-file=f.txt",
                                  "interactive=false", "multi-line=true"]) == \
        ["--log-file", "m", "--init-file", "i.txt", "--formula-file", "f.txt",
         "--no-interactive", "--multi-line"]
    assert normalize_legacy_argv(["interactive=true", "multi-line=false"]) == ["--interactive"]
    assert normalize_legacy_argv(["--log-file", "m", "log-file=n"]) == \
        ["--log-file", "m", "--log-file", "n"]


def test_parser_defaults():
    args = build_parser().parse_args(["--log-file", "m"])
    assert args.interactive is True
    assert args.multi_line is False
    assert args.init_file is None and args.formula_file is None and args.propositions is None


def test_missing_log_file_exits_2(capsys):
    with pytest.raises(SystemExit) as e:
        build_parser().parse_args([])
    assert e.value.code == 2


def test_no_arguments_shows_help(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err


def test_missing_files_exit_1(tmp_path, capsys):
    assert main(["--log-file", str(tmp_path / "nope")]) == 1
    assert "Error" in capsys.readouterr().err
    (tmp_path / "m.mod").write_text("aA\nt,x\n")
    assert main(["--log-file", str(tmp_path / "m"), "--init-file", "missing.txt"]) == 1


def test_read_lines_single():
    assert list(read_lines(io.StringIO("a\n\nb\n"))) == ["a", "", "b"]


def test_read_lines_multi():
    stream = io.StringIO("F (a &\n b) $ ignored\nG a$\ntail")
    assert list(read_lines(stream, multi_line=True)) == ["F (a & b) ", "G a", "tail"]


def test_prompt_is_printed_only_when_given(capsys):
    list(read_lines(io.StringIO("a\n"), prompt="DLTL -> "))
    out = capsys.readouterr()
    assert out.out == "DLTL -> DLTL -> "
    assert "EOF" in out.err
    list(read_lines(io.StringIO("a\n")))
    assert capsys.readouterr().out == ""
