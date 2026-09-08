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
"""SemanticDLTL: a model checker for DLTL (data-aware LTL with freeze operators) over finite traces.

Typical use as a library::

    from dltl import Log, Session

    session = Session(Log.load("examples/sample"))
    session.check_formula('F x.(b & "(x)x[V] == 10")')
    session.execute("_WRITE")
"""
__version__ = "1.0.0"

from dltl.evaluator import Evaluator, results_statistics  # noqa: E402
from dltl.log import Log  # noqa: E402
from dltl.parser import parse_formula  # noqa: E402
from dltl.session import CheckSummary, Session  # noqa: E402

__all__ = ["CheckSummary", "Evaluator", "Log", "Session", "parse_formula",
           "results_statistics", "__version__"]
