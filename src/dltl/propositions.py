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
propositions here, or in a separate Python file passed to the command-line
tool with ``--propositions my_props.py`` (any module attribute can then be
used as ``PROP.<name>``).

``COLUMNS`` is filled in by the session when a model is loaded; it maps each
non-atomic attribute name to its position in the event tuple, so that a
proposition receiving whole events can read attributes by name.
"""

COLUMNS: dict[str, int] = {}


def doble(x):
    return x * 2


def suma(x, y):
    return x + y


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


# x.(F y.("(x,y)PROP.TS_IG(x,y)"))
def TS_IG(x, y):
    """Events ``x`` and ``y`` have the same value of attribute ``V``."""
    V = COLUMNS['V']
    return x[V] == y[V]


# ---------------------------------------------------------------------------
# Examples working on rdflib graphs stored as attribute values.
# F x.(true & "(x)PROP.SP_HAS_VALUE(x[Details_g], 'duration', 'Ongoing')")

def SPARQL_old(g):
    query = """
        ASK
            WHERE {
               ?s <http://snomed.info/sct/duration> "Ongoing".
            }
            """
    return g.query(query).askAnswer


def SP_HAS_VALUE(g, predicado, objeto):
    query = f"""
                ASK
                    WHERE {{
                       ?s <http://snomed.info/sct/{predicado}> "{objeto}".
                    }}
            """
    return g.query(query).askAnswer
