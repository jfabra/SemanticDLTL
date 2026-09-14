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
Constructors and predicates for DLTL formula nodes.

A formula is a plain Python list whose first element is the set of *free
freeze variables* of the sub-formula and whose second element is the operator:

    [{...}, 'True']
    [{...}, 'False']
    [{...}, 'atom', 'z']        # 'z' is an atomic proposition
    [{...}, '!', exp]
    [{...}, 'F', exp]           # likewise 'O', 'X', 'Y', 'G', 'H'
    [{...}, '&', exp1, exp2]    # likewise '|', 'U', 'S'
    [{...}, 'fvar', 'z', exp]   # freeze: z.(exp)
    [{...}, 'exp', "(x,y)x[t]+y[t] > 3+PROP.f(7)"]
        The third element is a Python expression evaluated in the context of
        the trace. ``x`` and ``y`` are the freeze variables it depends on and
        ``PROP.f`` is a user-defined proposition (see ``dltl.propositions``).

IMPORTANT: only numeric fields can be used in numeric operations. You can
write ``"(x)x[V] > 1"`` if the attribute ``V`` was declared with type 'n'
(stored as a float), or ``"(x)x[p]['b'] == 2"`` if ``p`` is a dictionary
attribute whose value ``'b'`` is numeric.

Model checker based on the DLTL logic and algorithm in:
    J. M. Couvreur, J. Ezpeleta, "A Linear Temporal Logic Model Checking
    Method over Finite Words with Correlated Transition Attributes",
    SIMPDA 2017, LNBIP vol. 340, Springer, 2019.
"""

# Indexes inside a node: var set, operator, first and second sub-expression
v, t, e1, e2 = 0, 1, 2, 3

TRUE_VAL = [set(), 'True']
FALSE_VAL = [set(), 'False']


def is_false(exp) -> bool:
    return (len(exp[0]) == 0) and (exp[1] == 'False')


def is_true(exp) -> bool:
    return (len(exp[0]) == 0) and (exp[1] == 'True')


def TRUE():
    return TRUE_VAL.copy()


def FALSE():
    return FALSE_VAL.copy()


def atom(var):
    return [set(), 'atom', var]


def expression(vars, expression_string):
    return [vars, 'exp', expression_string]


def fvar(var, expression):
    return [{var}.union(expression[v]), 'fvar', var, expression]


def AND(exp1, exp2):
    return [exp1[v] | exp2[v], '&', exp1, exp2]


def OR(exp1, exp2):
    return [exp1[v] | exp2[v], '|', exp1, exp2]


def NOT(exp):
    return [exp[v], '!', exp]


def IMP(exp1, exp2):
    return OR(exp2, NOT(exp1))


def EQ(exp1, exp2):
    return AND(IMP(exp1, exp2), IMP(exp2, exp1))


# --- simplifying constructors ----------------------------------------------
# The evaluator builds nodes out of *partially evaluated* sub-formulas. A child
# that is already TRUE or FALSE fixes the value of its parent even when the
# parent still has free freeze variables, so the node can be folded on the spot
# instead of being carried along -- and copied by ``Evaluator.replace``, once
# per freeze position -- until those variables are bound.

def simp_and(exp1, exp2):
    """``AND`` folding the constant cases, with or without free variables."""
    if is_false(exp1) or is_false(exp2):
        return FALSE()
    if is_true(exp1):
        return exp2
    if is_true(exp2):
        return exp1
    return AND(exp1, exp2)


def simp_or(exp1, exp2):
    """``OR`` folding the constant cases, with or without free variables."""
    if is_true(exp1) or is_true(exp2):
        return TRUE()
    if is_false(exp1):
        return exp2
    if is_false(exp2):
        return exp1
    return OR(exp1, exp2)


def simp_not(exp):
    """``NOT`` folding the constant cases, with or without free variables."""
    if is_true(exp):
        return FALSE()
    if is_false(exp):
        return TRUE()
    return NOT(exp)


# --- future ----------------------------------------------------------------
def X(exp):
    return [exp[v], 'X', exp]


def Xn(n, exp):
    """X applied n times: X X ... X exp."""
    n = int(n)
    newExp = [exp[v], 'X', exp]
    for _ in range(n - 1):
        newExp = [exp[v], 'X', newExp]
    return newExp


def U(exp1, exp2):
    return [exp1[v] | exp2[v], 'U', exp1, exp2]


def G(exp):
    return [exp[v], 'G', exp]


def F(exp):
    return [exp[v], 'F', exp]


def Fn(n, exp):
    """exp holds now and at the next n-1 events."""
    n = int(n)
    if n == 1:
        return [exp[v], 'F', exp]
    return AND(exp, [exp[v], 'X', Fn(n - 1, exp)])


# --- past ------------------------------------------------------------------
def Y(exp):
    return [exp[v], 'Y', exp]


def Yn(n, exp):
    """Y applied n times: Y Y ... Y exp."""
    n = int(n)
    newExp = [exp[v], 'Y', exp]
    for _ in range(n - 1):
        newExp = [exp[v], 'Y', newExp]
    return newExp


def S(exp1, exp2):
    return [exp1[v] | exp2[v], 'S', exp1, exp2]


def O(exp):
    return [exp[v], 'O', exp]


def On(n, exp):
    """exp holds now and at the previous n-1 events."""
    n = int(n)
    if n == 1:
        return [exp[v], 'O', exp]
    return AND(exp, [exp[v], 'Y', On(n - 1, exp)])


def H(exp):
    return [exp[v], 'H', exp]
