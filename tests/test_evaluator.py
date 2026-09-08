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
import types

from dltl import formula as F_
from dltl.evaluator import Evaluator, results_statistics
from dltl.parser import parse_formula

COLUMNS = {"V": 1, "att": 2, "p": 3}


def ev(atoms, V=0.0, att=(), p=None):
    return (set(atoms), float(V), set(att), dict(p or {}))


TRACE = (ev("a", 4, "a", {"a": 1}),
         ev("a", 1, "a", {"a": 1}),
         ev("b", 1, "ax", {"a": 2}),
         ev("ab", 10, "a", {"a": 1}))


def truth(formula: str, trace=TRACE, props=None) -> list[bool]:
    node = parse_formula(formula)
    assert node is not None
    res = Evaluator(COLUMNS, props).eval_formula(node, trace)
    return [F_.is_true(r) for r in res]


def test_atoms_and_constants():
    assert truth("a") == [True, True, False, True]
    assert truth("b") == [False, False, True, True]
    assert truth("true") == [True] * 4
    assert truth("false") == [False] * 4


def test_propositional():
    assert truth("!a") == [False, False, True, False]
    assert truth("a & b") == [False, False, False, True]
    assert truth("a | b") == [True] * 4
    assert truth("a -> b") == [False, False, True, True]
    assert truth("a <-> b") == [False, False, False, True]


def test_next_and_last_event_idiom():
    assert truth("X a") == [True, False, True, False]
    assert truth("X false") == [False, False, False, True]
    assert truth("X2 b") == [True, True, False, False]


def test_previous_and_first_event_idiom():
    assert truth("Y a") == [False, True, True, False]
    assert truth("Y false") == [True, False, False, False]
    assert truth("Y2 a") == [False, False, True, True]


def test_future_operators():
    assert truth("F b") == [True] * 4
    assert truth("G a") == [False, False, False, True]
    assert truth("a U b") == [True] * 4
    assert truth("b U a") == [True, True, True, True]
    assert truth("(!b) U (b & !a)") == [True, True, True, False]
    assert truth("F2 a") == [True, True, False, False]


def test_past_operators():
    assert truth("O b") == [False, False, True, True]
    assert truth("H a") == [True, True, False, False]
    assert truth("b S a") == [True, True, True, True]
    assert truth("a S b") == [False, False, True, True]
    assert truth("O2 a") == [False, True, False, True]


def test_freeze_with_numeric_attribute():
    assert truth('x.("(x)x[V] == 1")') == [False, True, True, False]
    assert truth('F x.("(x)x[V] > 5")') == [True] * 4
    assert truth('G x.("(x)x[V] >= 1")') == [True] * 4


def test_freeze_with_set_and_dict_attributes():
    # the variable name must not appear inside string literals of the expression
    assert truth('y.("(y)\'x\' in y[att]")') == [False, False, True, False]
    assert truth('x.("(x)x[p][\'a\'] == 2")') == [False, False, True, False]
    assert truth('x.("(x)COL[\'V\'] == 1 and x[COL[\'V\']] == 4")') == [True, False, False, False]


def test_event_position():
    assert truth('x.("(x)x[#] == 3")') == [False, False, True, False]
    assert truth('x.(X y.("(x,y)y[#] == x[#] + 1"))') == [True, True, True, False]


def test_two_frozen_events():
    # some later event has the same V
    assert truth('x.(X F y.("(x,y)x[V] == y[V]"))') == [False, True, False, False]
    assert truth('F x.(b & X y.("(x,y)x[V] < y[V]"))') == [True, True, True, False]


def test_default_propositions():
    assert truth('x.("(x)PROP.IN_DIC(x[p], \'a\', 2)")') == [False, False, True, False]
    assert truth('x.("(x)PROP.IN_DIC_2(x, p, \'a\', 1)")') == [True, True, False, True]


def test_custom_propositions_module():
    props = types.ModuleType("user_props")
    props.COLUMNS = {}
    props.big = lambda e: e[props.COLUMNS["V"]] >= 4
    props.COLUMNS = COLUMNS
    assert truth('x.("(x)PROP.big(x)")', props=props) == [True, False, False, True]


def test_variable_free_data_expression():
    assert truth('"()1 + 1 == 2"') == [True] * 4


def test_results_statistics():
    node = parse_formula("a")
    res = Evaluator(COLUMNS).eval_formula(node, TRACE)
    assert results_statistics(res) == (1, 3, 1, 0.75)
    node = parse_formula("b")
    res = Evaluator(COLUMNS).eval_formula(node, TRACE)
    assert results_statistics(res) == (0, 2, 2, 0.5)


def test_evaluation_error_yields_false(capsys):
    assert truth('x.("(x)x[V] / 0 > 1")') == [False] * 4
    assert "ZeroDivisionError" in capsys.readouterr().err
