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
import pytest

from dltl import formula as F_
from dltl.parser import Parser, lexer, parse_formula


def parse(s):
    return Parser(lexer(s)).parse()


def test_atoms_true_false():
    assert parse("a") == [set(), 'atom', 'a']
    assert parse("true") == F_.TRUE()
    assert parse("false") == F_.FALSE()


def test_same_atom_is_shared():
    p = Parser(lexer("a & a"))
    node = p.parse()
    assert node[2] is node[3]


def test_unary_operators():
    a = F_.atom('a')
    for text, ctor in [("!a", F_.NOT), ("X a", F_.X), ("Y a", F_.Y), ("G a", F_.G),
                       ("H a", F_.H), ("F a", F_.F), ("O a", F_.O)]:
        assert parse(text) == ctor(a)


def test_numbered_operators_expand():
    a = F_.atom('a')
    assert parse("X3 a") == F_.X(F_.X(F_.X(a)))
    assert parse("Y2 a") == F_.Y(F_.Y(a))
    assert parse("F2 a") == F_.AND(a, F_.X(F_.F(a)))
    assert parse("O2 a") == F_.AND(a, F_.Y(F_.O(a)))


def test_binary_operators_and_implication():
    a, b = F_.atom('a'), F_.atom('b')
    assert parse("a U b") == F_.U(a, b)
    assert parse("a S b") == F_.S(a, b)
    assert parse("a -> b") == F_.IMP(a, b)
    assert parse("a <-> b") == F_.EQ(a, b)


def test_precedence():
    a, b, c = F_.atom('a'), F_.atom('b'), F_.atom('c')
    assert parse("F a U b") == F_.U(F_.F(a), b)
    assert parse("!X a") == F_.NOT(F_.X(a))
    assert parse("a U b & c") == F_.AND(F_.U(a, b), c)
    assert parse("a -> b & c") == F_.IMP(a, F_.AND(b, c))
    assert parse("(a | b) & c") == F_.AND(F_.OR(a, b), c)


def test_and_or_precedence():
    # `&` binds tighter than `|` (see docs/grammar.md)
    a, b, c = F_.atom('a'), F_.atom('b'), F_.atom('c')
    assert parse("a | b & c") == F_.OR(a, F_.AND(b, c))
    assert parse("a & b | c") == F_.OR(F_.AND(a, b), c)


def test_left_associativity():
    a, b, c = F_.atom('a'), F_.atom('b'), F_.atom('c')
    assert parse("a & b & c") == F_.AND(F_.AND(a, b), c)


def test_freeze_and_data_expression():
    node = parse('F x.(b & "(x)x[V]==10")')
    assert node == F_.F(F_.fvar('x', F_.AND(F_.atom('b'), F_.expression({'x'}, 'x[V]==10'))))
    assert node[0] == {'x'}          # the freeze node records its own variable
    assert node[2][3][0] == {'x'}    # ... but free inside


def test_data_expression_with_two_vars_and_no_vars():
    assert parse('"(x,y)x[V]==y[V]"') == F_.expression({'x', 'y'}, 'x[V]==y[V]')
    assert parse('"()1==1"') == F_.expression(set(), '1==1')


def test_data_expression_unescapes_quotes():
    assert parse('"(x)x[p][\\\'b\\\']==22"') == F_.expression({'x'}, "x[p]['b']==22")


def test_dollar_is_ignored():
    assert parse("F a $") == F_.F(F_.atom('a'))


def test_syntax_errors():
    with pytest.raises(SyntaxError):
        parse("a &")
    with pytest.raises(SyntaxError):
        parse("a b")
    with pytest.raises(SyntaxError):
        parse("a # b")
    assert parse_formula("a &") is None
