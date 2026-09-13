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
Default user-defined propositions.

This module is available as ``PROP`` inside the data expressions of DLTL
formulas, e.g. ``x.("(x)PROP.IN_DIC(x[p], 'b', 3)")``. Write your own
propositions here, in a separate Python file passed to the command-line tool
with ``--propositions my_props.py``, or in a file loaded during the session
with ``_LOAD name my_props.py`` (usable then as ``name.<function>``).

``COLUMNS`` is filled in by the session when a model is loaded; it maps each
non-atomic attribute name to its position in the event tuple, so that a
proposition receiving whole events can read attributes by name. ``I_POS`` and
``I_ATOM`` are the positions of the event position and of its set of atomic
propositions.
"""
import re

from dltl.log import I_ATOM, I_POS  # noqa: F401  (re-exported for user code)

COLUMNS: dict[str, int] = {}


def quote(s):
    return '"' + s + '"'


# x.("(x)PROP.IN_DIC(x[p],'b',3)")
def IN_DIC(dicc, k, v):
    """True when dictionary ``dicc`` maps key ``k`` to value ``v``."""
    return k in dicc and dicc[k] == v


# x.("(x)PROP.IN_DIC_2(x,p,'b',22)")
def IN_DIC_2(event, posDir, k, v):
    """Like ``IN_DIC`` but receiving the whole event and the attribute position."""
    return k in event[posDir] and event[posDir][k] == v


# x.(F y.("(x,y)PROP.SAME_KEY_VALUE(x[p], y[p], 'b')"))
def SAME_KEY_VALUE(dic1, dic2, k):
    """Both dictionaries have key ``k`` with the same value."""
    return k in dic1 and k in dic2 and dic1[k] == dic2[k]


# x.("(x)PROP.check_patt(x[name], 'ac_.*')")
def check_patt(attContent, pattern):
    """The regular expression ``pattern`` matches somewhere in the string."""
    return bool(re.search(pattern, attContent))


def check_patt_f(pattern):
    """Build a case-insensitive matcher for ``pattern``: ``PROP.check_patt_f('x')(s)``."""
    rx = re.compile(pattern, re.IGNORECASE)
    return lambda s: bool(rx.search(s))


# x.(F y.("(x,y)PROP.diff_att_geq(x[V], y[V], 3)"))
def diff_att_geq(x, y, value):
    """``y - x >= value`` for two attribute values."""
    return y - x >= value


# x.(X X y.("(x,y)PROP.diff_pos(x, y, 2)"))
def diff_pos(x, y, diff):
    """Event ``y`` is exactly ``diff`` positions after event ``x``."""
    return y[I_POS] == x[I_POS] + diff


# x.("(x)PROP.has_f_value(x, V, 3.0)")
def has_f_value(x, attrib, value, epsilon=1e-6):
    """The float attribute at position ``attrib`` of event ``x`` equals ``value``."""
    return abs(x[attrib] - value) <= epsilon


# F x.(id_0 & F y.(id_1 & "(x,y)PROP.near(x, y, 12)"))
def near(x, y, dist):
    """Events ``x`` and ``y`` happen at the same time and at most ``dist`` apart.

    Requires numeric attributes ``time`` and ``pos`` in the model.
    Pre: ``x`` is not later than ``y`` in the trace.
    """
    time, pos = COLUMNS['time'], COLUMNS['pos']
    return y[time] - x[time] <= 1e-6 and abs(y[pos] - x[pos]) <= dist
