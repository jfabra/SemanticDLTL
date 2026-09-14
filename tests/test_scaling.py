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
"""The cost of a freeze must follow the events that can satisfy it, not the trace length.

Before the partially evaluated formulas were folded and short-circuited, a
nested freeze rebuilt the whole suffix of the trace for *every* event, which
made these formulas quadratic in time and memory (unusable on the million-event
logs they are meant for). These tests pin the number of data expressions that
are actually evaluated, which is what used to explode.
"""
from dltl import formula as F_
from dltl.evaluator import Evaluator
from dltl.parser import parse_formula

COLUMNS = {"T": 2}
N = 1500


def trace(atoms_at: dict[int, str]) -> tuple:
    """Trace of ``N`` events; ``atoms_at`` gives the atoms of some positions.

    Every other event is a filler ``c``. The attribute ``T`` is the position,
    so that ``y[T] - x[T]`` is the distance between two events.
    """
    return tuple((i + 1, set(atoms_at.get(i, "c")), float(i)) for i in range(N))


def check(formula: str, trace) -> tuple[list[bool], int]:
    """Evaluate ``formula`` and count how many data expressions were evaluated."""
    evaluator = Evaluator(COLUMNS)
    calls = 0
    inner = evaluator._eval_data

    def counting(expression):
        nonlocal calls
        calls += 1
        return inner(expression)

    evaluator._eval_data = counting
    node = parse_formula(formula)
    assert node is not None
    res = evaluator.eval_formula(node, trace)
    return [F_.is_true(r) for r in res], calls


def test_nested_freeze_only_visits_the_relevant_events():
    # two 'a' events and one 'b' event in a trace of 1500: the formula can only
    # be decided at those, so only a handful of data expressions are evaluated
    # (it used to be one per pair of events, ~10^6)
    t = trace({10: "a", 1200: "a", 1210: "b"})
    truth, calls = check('F(x.(a & F(y.(b & "(x,y)y[T]-x[T]<=100"))))', t)
    assert truth[:1201] == [True] * 1201          # 'a' at 1200 has 'b' at 1210
    assert truth[1201:] == [False] * (N - 1201)   # nothing left afterwards
    assert calls <= 10


def test_the_disjunction_of_F_stops_at_the_first_match():
    # every event satisfies the inner formula, so each frozen event settles it
    # with a single data expression instead of scanning the whole suffix
    t = trace({i: "ab" for i in range(N)})
    truth, calls = check('F(x.(a & F(y.(b & "(x,y)y[T]>=x[T]"))))', t)
    assert truth == [True] * N
    assert calls <= 3 * N


def test_the_conjunction_of_G_stops_at_the_first_failure():
    t = trace({i: "ab" for i in range(N)})
    truth, calls = check('F(x.(a & G(y.(b & "(x,y)y[T]<x[T]"))))', t)
    assert truth == [False] * N
    assert calls <= 3 * N
