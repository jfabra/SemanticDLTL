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
Lexer and Pratt parser for DLTL formulas.

``parse_formula`` turns a formula string such as ``F x.(b & "(x)x[V] > 3")``
into the list-based node structure described in :mod:`dltl.formula`.
"""
import ast
import re
import sys

from dltl import formula as F_

# ---------------------------------------------------------------------------
# Lexer


class Token:
    __slots__ = ("type", "value")

    def __init__(self, type_, value=None):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"


TOKEN_SPEC = [
    ('LPAREN',   r'\('),
    ('RPAREN',   r'\)'),
    ('NOT',      r'!'),

    ('AND',      r'&'),
    ('OR',       r'\|'),
    ('IMP',      r'->'),
    ('EQ',       r'<->'),

    ('TRUE',     r'true'),
    ('FALSE',    r'false'),
    # data expression: "(x,y)<python expression>"
    ('STRING',   r'"\(([a-zA-Z]+(,[a-zA-Z]+)*)?\)[^"\n\r\t]*"'),
    ('FREEZE',   r'[a-z]\.'),
    ('U',        r'\bU\b'),
    ('S',        r'\bS\b'),
    ('X',        r'\bX\b'),
    ('Xn',       r'\bX[1-9]+\b'),
    ('Y',        r'\bY\b'),
    ('Yn',       r'\bY[1-9]+\b'),
    ('G',        r'\bG\b'),
    ('H',        r'\bH\b'),
    ('F',        r'\bF\b'),
    ('Fn',       r'\bF[1-9]+\b'),
    ('O',        r'\bO\b'),
    ('On',       r'\bO[1-9]+\b'),

    ('ID',       r'[a-zA-Z_][a-zA-Z_0-9]*'),

    ('SKIP',     r'[ \t\n$]+'),
    ('ERROR',    r'.'),
]
_TOKEN_RE = re.compile('|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPEC))


def lexer(text: str) -> list[Token]:
    tokens = []
    pos = 0
    mo = _TOKEN_RE.match(text, pos)
    while mo:
        typ = mo.lastgroup
        if typ == 'SKIP':
            pass
        elif typ == 'ERROR':
            raise SyntaxError(f"Unexpected character: {mo.group()}")
        else:
            tokens.append(Token(typ, mo.group()))
        pos = mo.end()
        mo = _TOKEN_RE.match(text, pos)
    tokens.append(Token('EOF'))
    return tokens


# ---------------------------------------------------------------------------
# Parser

BINARY = {'AND': F_.AND, 'OR': F_.OR, 'IMP': F_.IMP, 'EQ': F_.EQ, 'U': F_.U, 'S': F_.S}
PREFIX = {'NOT': F_.NOT, 'X': F_.X, 'Y': F_.Y, 'G': F_.G, 'H': F_.H, 'F': F_.F, 'O': F_.O}
PREFIX_N = {'Xn': F_.Xn, 'Yn': F_.Yn, 'Fn': F_.Fn, 'On': F_.On}


class Parser:
    """Pratt parser: binary operators are left-associative, higher level binds tighter."""

    PRECEDENCE = {
        'IMP': 0, 'EQ': 0,
        'AND': 2,
        'OR': 1,
        'U': 3, 'S': 3,
        'F': 4, 'O': 4, 'Fn': 4, 'On': 4,
        'G': 5, 'H': 5,
        'X': 6, 'Y': 6, 'Xn': 6, 'Yn': 6,
        'NOT': 7,
    }

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        # one node per atomic proposition, shared by all its occurrences
        self.atoms: dict[str, list] = {}

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def consume(self, *expected) -> Token:
        token = self.peek()
        if token.type in expected:
            self.pos += 1
            return token
        raise SyntaxError(f"Expected {expected}, got {token}")

    def parse(self):
        node = self.parse_expr(0)
        if self.peek().type != 'EOF':
            raise SyntaxError(f"Unexpected token: {self.peek()}")
        return node

    def parse_expr(self, min_prec: int):
        left = self.parse_prefix()
        while True:
            tok = self.peek()
            if tok.type not in BINARY:
                break
            prec = self.PRECEDENCE[tok.type]
            if prec < min_prec:
                break
            self.consume(tok.type)
            right = self.parse_expr(prec + 1)
            left = BINARY[tok.type](left, right)
        return left

    def parse_prefix(self):
        tok = self.peek()

        if tok.type == 'LPAREN':
            self.consume('LPAREN')
            expr = self.parse_expr(0)
            self.consume('RPAREN')
            return expr

        if tok.type in PREFIX_N:
            op = self.consume(tok.type)
            n = int(op.value[1:])
            return PREFIX_N[op.type](n, self.parse_expr(self.PRECEDENCE[op.type]))

        if tok.type in PREFIX:
            op = self.consume(tok.type)
            return PREFIX[op.type](self.parse_expr(self.PRECEDENCE[op.type]))

        if tok.type == 'STRING':
            return self.parse_data_expression(self.consume('STRING').value)

        if tok.type == 'TRUE':
            self.consume('TRUE')
            return F_.TRUE()

        if tok.type == 'FALSE':
            self.consume('FALSE')
            return F_.FALSE()

        if tok.type == 'FREEZE':
            var = self.consume('FREEZE').value[:-1]
            self.consume('LPAREN')
            arg = self.parse_expr(0)
            self.consume('RPAREN')
            return F_.fvar(var, arg)

        if tok.type == 'ID':
            name = self.consume('ID').value
            if name not in self.atoms:
                self.atoms[name] = F_.atom(name)
            return self.atoms[name]

        raise SyntaxError(f"Unexpected token: {tok.type}:{tok}")

    @staticmethod
    def parse_data_expression(token_value: str):
        """``"(x,y)x[#]+x[ts]>100"`` -> ``expression({'x','y'}, 'x[#]+x[ts]>100')``."""
        val = token_value.strip('"')
        paren_close = val.index(')')
        vars_part = val[1:paren_close]
        body = val[paren_close + 1:]
        var_set = set(vars_part.split(',')) if vars_part else set()
        # The body is interpreted as a Python string literal so that escape
        # sequences (e.g. \') behave as they always did.
        body = ast.literal_eval('"' + body + '"')
        return F_.expression(var_set, body)


# ---------------------------------------------------------------------------

def parse_formula(s: str):
    """Parse a DLTL formula; returns the node or ``None`` (after printing) on a syntax error."""
    try:
        return Parser(lexer(s)).parse()
    except SyntaxError as e:
        print(f"Syntax error: {e}", file=sys.stderr)
        return None


parse_expression = parse_formula  # backward-compatible name
