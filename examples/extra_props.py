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
"""Extra propositions loaded during a session with the ``_LOAD`` command.

    DLTL -> _LOAD mp examples/extra_props.py
    DLTL -> F x.("(x)mp.f(x[V]) == mp.C * 8")

``COLUMNS`` is filled in by the session with the attribute positions of the
loaded model, as in the default propositions module.
"""

COLUMNS: dict[str, int] = {}

C = 1


def f(x):
    """Twice ``x``."""
    return 2 * x


def has_V(event, value):
    """The event has attribute ``V`` equal to ``value``."""
    return event[COLUMNS['V']] == value
