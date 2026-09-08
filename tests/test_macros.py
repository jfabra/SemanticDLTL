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
from dltl.macros import unfold_macros


def test_no_macros():
    assert unfold_macros("F a", {"?x": ("1", "2")}) == ["F a"]


def test_single_macro():
    assert unfold_macros("F ?act", {"?act": ("load", "mark")}) == ["F load", "F mark"]


def test_cartesian_product():
    out = unfold_macros("?a U ?b", {"?a": ("x", "y"), "?b": ("1", "2")})
    assert sorted(out) == ["x U 1", "x U 2", "y U 1", "y U 2"]


def test_longest_key_first():
    out = unfold_macros("F ?ac", {"?a": ("BAD",), "?ac": ("ok",)})
    assert out == ["F ok"]


def test_cycle_is_bounded(capsys):
    out = unfold_macros("?a", {"?a": ("?a",)})
    assert out == []
    assert "max iterations" in capsys.readouterr().err
