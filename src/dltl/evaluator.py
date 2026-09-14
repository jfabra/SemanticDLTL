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
"""
Evaluation of DLTL formulas over a finite trace.

The evaluation is bottom-up and per trace: ``Evaluator.eval_formula`` returns a
list with one (partially evaluated) node per event, the node at position ``i``
being the value of the formula at event ``i``. When a formula contains no free
freeze variables that node is simply ``TRUE()`` or ``FALSE()``.

Model checker based on the DLTL logic and algorithm in:
    J. M. Couvreur, J. Ezpeleta, "A Linear Temporal Logic Model Checking
    Method over Finite Words with Correlated Transition Attributes",
    SIMPDA 2017, LNBIP vol. 340, Springer, 2019.
"""
from __future__ import annotations

import re
import sys
import traceback
from types import ModuleType
from typing import Any

from dltl.formula import (
    FALSE,
    TRUE,
    e1,
    e2,
    is_false,
    is_true,
    simp_and,
    simp_not,
    simp_or,
    t,
    v,
)
from dltl.log import I_ATOM, I_POS

# Name under which the current trace is visible inside data expressions after
# the freeze variables have been substituted ("x[V]" -> "THE_TRACE[3][V]").
TRACE_NAME = 'THE_TRACE'

_UNARY_OPS = frozenset({'atom', '!', 'X', 'G', 'F', 'Y', 'H', 'O'})
_BINARY_OPS = frozenset({'&', '|', 'U', 'S'})


class Evaluator:
    """Evaluates formulas over traces of a given model.

    ``column_index`` maps attribute names to positions in the event tuple (see
    :class:`dltl.log.Log`), and ``props`` is the module exposed as ``PROP``
    inside data expressions. Both, together with the current trace, form the
    namespace in which data expressions are ``eval``'d.
    """

    def __init__(self, column_index: dict[str, int], props: ModuleType | None = None):
        if props is None:
            from dltl import propositions as props
        self._ns: dict[str, Any] = {**column_index,
                                    'COL': dict(column_index),
                                    'I_POS': I_POS,
                                    'I_ATOM': I_ATOM,
                                    'PROP': props,
                                    TRACE_NAME: ()}
        self._cases = {
            'X': self.eval_X, 'U': self.eval_U, 'F': self.eval_F, 'G': self.eval_G,
            'Y': self.eval_Y, 'S': self.eval_S, 'O': self.eval_O, 'H': self.eval_H,
            'True': self.eval_True_False, 'False': self.eval_True_False,
            '!': self.eval_Not, '&': self.eval_AND, '|': self.eval_OR,
            'fvar': self.eval_fvar, 'exp': self.eval_exp, 'atom': self.eval_atom,
        }

    def add_module(self, name: str, module: ModuleType) -> None:
        """Make ``module`` available as ``name`` inside data expressions (``_LOAD``)."""
        self._ns[name] = module

    # ------------------------------------------------------------------
    def eval_formula(self, exp, trace) -> list:
        """Evaluate ``exp`` at every event of ``trace``; one node per event."""
        self._ns[TRACE_NAME] = trace
        try:
            return self._cases[exp[t]](exp, trace)
        except Exception as e:  # noqa: BLE001 - report and keep the session alive
            print(f"An error occurred: {e}", file=sys.stderr)
            print("\n--- Full Traceback ---", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print("returning FALSE value\n", file=sys.stderr)
            print("----------------------\n", file=sys.stderr)
            return [FALSE() for _ in trace]

    def _eval_data(self, expression: str):
        return eval(expression, self._ns)  # noqa: S307 - data expressions are user code by design

    # ------------------------------------------------------------------
    def replace(self, traza, i, exp, var):
        """Substitute freeze variable ``var`` by event ``i`` in ``exp``.

        ``var[#]`` becomes the (1-based) position of the event and any other
        occurrence of ``var`` becomes ``THE_TRACE[i]``. Data expressions left
        without free variables are evaluated on the spot.
        """
        # everything that depends only on (i, var) is computed once per call
        var_set = frozenset({var})
        position = str(i + 1)              # first event position is 1, not 0
        trace_ref = f"{TRACE_NAME}[{i}]"
        var_hash = f"{var}[#]"
        pattern = re.compile(rf'\b{re.escape(var)}\b')

        # (form, 0): descendants not processed yet
        # (form, 1): first operand of a '&' / '|' resolved, second one pending
        # (form, 2): every needed descendant is resolved and stored in resultMap
        stack = [(exp, 0)]
        resultMap = {}

        while stack:
            theForm, stage = stack.pop()
            form_id = id(theForm)
            if form_id in resultMap:
                continue

            vars = theForm[v]
            op = theForm[t]

            if var not in vars or is_false(theForm) or is_true(theForm):
                resultMap[form_id] = theForm
                continue

            if stage == 1:
                # short circuit: the second operand is only substituted (and its
                # data expressions only evaluated) if the first one leaves the
                # result open. This is what makes "x.(F(y.(...)))" stop at the
                # first event that settles the formula instead of rebuilding the
                # whole suffix for every frozen event.
                first = resultMap[id(theForm[e1])]
                settled = is_false(first) if op == '&' else is_true(first)
                if settled:
                    resultMap[form_id] = FALSE() if op == '&' else TRUE()
                else:
                    stack.append((theForm, 2))
                    stack.append((theForm[e2], 0))
                continue

            if stage == 2:  # descendant results are already in resultMap
                new_vars = vars - var_set
                # folding here is what keeps the substituted formula small: as
                # soon as a data expression becomes True/False its whole branch
                # usually collapses instead of being rebuilt event by event
                if op == '&':
                    resultMap[form_id] = simp_and(resultMap[id(theForm[e1])],
                                                  resultMap[id(theForm[e2])])
                elif op == '|':
                    resultMap[form_id] = simp_or(resultMap[id(theForm[e1])],
                                                 resultMap[id(theForm[e2])])
                elif op == '!':
                    resultMap[form_id] = simp_not(resultMap[id(theForm[e1])])
                elif op in _UNARY_OPS:
                    resultMap[form_id] = [new_vars, op, resultMap[id(theForm[e1])]]
                elif op in _BINARY_OPS:
                    resultMap[form_id] = [new_vars, op,
                                          resultMap[id(theForm[e1])],
                                          resultMap[id(theForm[e2])]]
                elif op == 'fvar':
                    resultMap[form_id] = [new_vars, op, theForm[e1], resultMap[id(theForm[e2])]]
                elif op == 'exp':
                    newFormula = theForm[e1].replace(var_hash, position)
                    newFormula = pattern.sub(trace_ref, newFormula)
                    if not new_vars:
                        resultMap[form_id] = [new_vars, str(self._eval_data(newFormula))]
                    else:
                        resultMap[form_id] = [new_vars, op, newFormula]
            else:
                # postorder: reinsert and process the descendants first
                if op in ('&', '|'):
                    stack.append((theForm, 1))
                    stack.append((theForm[e1], 0))
                elif op in _UNARY_OPS:
                    stack.append((theForm, 2))
                    stack.append((theForm[e1], 0))
                elif op in _BINARY_OPS:
                    stack.append((theForm, 2))
                    stack.append((theForm[e1], 0))
                    stack.append((theForm[e2], 0))
                elif op == 'fvar':
                    stack.append((theForm, 2))
                    stack.append((theForm[e2], 0))
                else:  # 'exp': no descendants
                    stack.append((theForm, 2))

        return resultMap[id(exp)]

    # ------------------------------------------------------------------
    def eval_formula_in_event(self, exp, i, traza):
        """Simplify ``exp`` at event ``i`` as far as its free variables allow."""
        # (exp, False): children not yet processed
        # (exp, True): children already resolved and their value stored in resultMap
        stack = [(exp, False)]
        resultMap = {}

        while stack:
            theForm, visited = stack.pop()

            if id(theForm) in resultMap:
                continue

            vars = theForm[v]
            op = theForm[t]

            # true or false, or non-evaluable because of the vars
            if len(vars) != 0 or is_false(theForm) or is_true(theForm):
                resultMap[id(theForm)] = theForm
                continue

            if visited:
                if op == 'exp':
                    val = theForm[e1]
                    try:
                        val_str = str(self._eval_data(str(val)))
                    except Exception as ex:  # noqa: BLE001
                        print(f"Eval error in 'exp': {ex}", file=sys.stderr)
                        val_str = "False"
                    resultMap[id(theForm)] = [set(), val_str]
                elif op == 'atom':
                    resultMap[id(theForm)] = TRUE() if theForm[e1] in traza[i][I_ATOM] else FALSE()
                elif op == '&':
                    ev1 = resultMap[id(theForm[e1])]
                    ev2 = resultMap[id(theForm[e2])]
                    if is_false(ev1) or is_false(ev2):
                        resultMap[id(theForm)] = FALSE()
                    elif is_true(ev1) and is_true(ev2):
                        resultMap[id(theForm)] = TRUE()
                    elif is_true(ev1):
                        resultMap[id(theForm)] = ev2
                    elif is_true(ev2):
                        resultMap[id(theForm)] = ev1
                    else:
                        resultMap[id(theForm)] = [ev1[0] | ev2[0], '&', ev1, ev2]
                elif op == '|':
                    ev1 = resultMap[id(theForm[e1])]
                    ev2 = resultMap[id(theForm[e2])]
                    if is_true(ev1) or is_true(ev2):
                        resultMap[id(theForm)] = TRUE()
                    elif is_false(ev1):
                        resultMap[id(theForm)] = ev2
                    elif is_false(ev2):
                        resultMap[id(theForm)] = ev1
                    else:
                        resultMap[id(theForm)] = [ev1[0] | ev2[0], '|', ev1, ev2]
                elif op == '!':
                    ev = resultMap[id(theForm[e1])]
                    if len(ev[0]) == 0:
                        resultMap[id(theForm)] = FALSE() if ev[1] == 'True' else TRUE()
                    else:
                        resultMap[id(theForm)] = [ev[0], '!', ev]
                elif op == 'fvar':
                    new_exp = self.replace(traza, i, theForm[e2], theForm[e1])
                    stack.append((new_exp, False))
                    stack.append((theForm, True))  # cannot be resolved yet
            else:
                stack.append((theForm, True))
                # preorder: descendants first
                if op in {'&', '|'}:
                    stack.append((theForm[e2], False))
                    stack.append((theForm[e1], False))
                elif op == '!':
                    stack.append((theForm[e1], False))
                # 'fvar' is handled in the post-processing step; 'atom'/'exp' have no children

        return resultMap[id(exp)]

    # ------------------------------------------------------------------
    # future operators
    def eval_X(self, exp, traza):
        n = len(traza)
        res = [None] * n
        # "X false" is the idiom for "last event": it holds only there
        res[n - 1] = TRUE() if is_false(exp[e1]) else FALSE()
        eval_exp = self.eval_formula(exp[e1], traza)
        for i in reversed(range(n - 1)):
            res[i] = eval_exp[i + 1]
        return res

    def eval_U(self, exp, traza):
        n = len(traza)
        res = [None] * n
        res_f = self.eval_formula(exp[e1], traza)
        res_g = self.eval_formula(exp[e2], traza)
        res[n - 1] = res_g[n - 1]
        for i in reversed(range(n - 1)):
            res[i] = self.eval_formula_in_event(
                simp_or(res_g[i], simp_and(res_f[i], res[i + 1])), i, traza)
        return res

    def eval_F(self, exp, traza):
        n = len(traza)
        res = [None] * n
        res_parcial = self.eval_formula(exp[e1], traza)
        res[n - 1] = self.eval_formula_in_event(res_parcial[n - 1], n - 1, traza)
        already_true = is_true(res[n - 1])
        for i in reversed(range(n - 1)):
            if already_true:  # F f holds at i+1, hence at every earlier event
                res[i] = TRUE()
            else:
                res[i] = self.eval_formula_in_event(simp_or(res_parcial[i], res[i + 1]), i, traza)
                already_true = is_true(res[i])
        return res

    def eval_G(self, exp, traza):
        n = len(traza)
        res = [None] * n
        res_parcial = self.eval_formula(exp[e1], traza)
        res[n - 1] = self.eval_formula_in_event(res_parcial[n - 1], n - 1, traza)
        already_false = is_false(res[n - 1])
        for i in reversed(range(n - 1)):
            if already_false:  # G f fails at i+1, hence at every earlier event
                res[i] = FALSE()
            else:
                res[i] = self.eval_formula_in_event(simp_and(res_parcial[i], res[i + 1]), i, traza)
                already_false = is_false(res[i])
        return res

    # past operators
    def eval_Y(self, exp, traza):
        n = len(traza)
        res = [None] * n
        # "Y false" is the idiom for "first event": it holds only there
        res[0] = TRUE() if is_false(exp[e1]) else FALSE()
        res_exp = self.eval_formula(exp[e1], traza)
        for i in range(1, n):
            res[i] = res_exp[i - 1]
        return res

    def eval_S(self, exp, traza):
        n = len(traza)
        res = [None] * n
        res_f = self.eval_formula(exp[e1], traza)
        res_g = self.eval_formula(exp[e2], traza)
        res[0] = res_g[0]
        for i in range(1, n):
            res[i] = self.eval_formula_in_event(
                simp_or(res_g[i], simp_and(res_f[i], res[i - 1])), i, traza)
        return res

    def eval_O(self, exp, traza):
        n = len(traza)
        res = [None] * n
        res_f = self.eval_formula(exp[e1], traza)
        res[0] = self.eval_formula_in_event(res_f[0], 0, traza)
        already_true = is_true(res[0])
        for i in range(1, n):
            if already_true:  # O f holds at i-1, hence at every later event
                res[i] = TRUE()
            else:
                res[i] = self.eval_formula_in_event(simp_or(res_f[i], res[i - 1]), i, traza)
                already_true = is_true(res[i])
        return res

    def eval_H(self, exp, traza):
        n = len(traza)
        res = [None] * n
        res_f = self.eval_formula(exp[e1], traza)
        res[0] = self.eval_formula_in_event(res_f[0], 0, traza)
        already_false = is_false(res[0])
        for i in range(1, n):
            if already_false:  # H f fails at i-1, hence at every later event
                res[i] = FALSE()
            else:
                res[i] = self.eval_formula_in_event(simp_and(res_f[i], res[i - 1]), i, traza)
                already_false = is_false(res[i])
        return res

    # propositional operators and leaves
    def eval_True_False(self, exp, traza):
        return [[set(), exp[t]] for _ in traza]

    def eval_Not(self, exp, traza):
        res_f = self.eval_formula(exp[e1], traza)
        return [self.eval_formula_in_event(simp_not(res_f[i]), i, traza)
                for i in range(len(traza))]

    def eval_AND(self, exp, traza):
        res_f1 = self.eval_formula(exp[e1], traza)
        res_f2 = self.eval_formula(exp[e2], traza)
        return [self.eval_formula_in_event(simp_and(res_f1[i], res_f2[i]), i, traza)
                for i in range(len(traza))]

    def eval_OR(self, exp, traza):
        res_f1 = self.eval_formula(exp[e1], traza)
        res_f2 = self.eval_formula(exp[e2], traza)
        return [self.eval_formula_in_event(simp_or(res_f1[i], res_f2[i]), i, traza)
                for i in range(len(traza))]

    def eval_fvar(self, exp, traza):
        freezeVar = exp[e1]
        row = self.eval_formula(exp[e2], traza)
        # substitution and simplification are fused: the formula substituted at
        # an event is reduced (usually to True/False) before the next one is
        # built, so only one substituted formula is alive at a time
        return [self.eval_formula_in_event(self.replace(traza, i, row[i], freezeVar), i, traza)
                for i in range(len(traza))]

    def eval_exp(self, exp, traza):
        return [self.eval_formula_in_event(exp, i, traza) for i in range(len(traza))]

    def eval_atom(self, exp, traza):
        return [TRUE() if exp[e1] in event[I_ATOM] else FALSE() for event in traza]


# ---------------------------------------------------------------------------

def results_statistics(res) -> tuple[int, int, int, float]:
    """Summarise the per-event results of a formula over one trace.

    Returns ``(holds, true_count, false_count, ratio)`` where ``holds`` is 1
    when the formula is true at the first event (the classic model checking
    answer) and ``ratio`` is the fraction of events where it is true.

    Raises ``ValueError`` if some event was left with an unresolved node.
    """
    n = len(res)
    trueCount = sum(1 for r in res if is_true(r))
    falseCount = sum(1 for r in res if is_false(r))
    if trueCount + falseCount != n:
        raise ValueError(f"unresolved evaluation: {trueCount + falseCount} != {n}")
    return (1 if is_true(res[0]) else 0), trueCount, falseCount, trueCount / n
