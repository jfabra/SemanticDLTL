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
"""Macro expansion for formulas typed in a session (``_SET``, ``_RE``, ``_RANGE``)."""
import sys

MAX_ITERATIONS = 1000  # guard against cyclic macro definitions


def unfold_macros(formula: str, macroDict: dict[str, tuple[str, ...]]) -> list[str]:
    """Expand every macro occurring in ``formula``.

    Given a formula possibly containing macros such as ``?activities`` and a
    dictionary ``{'?activities': ('load', 'mark', 'unload'), ...}``, returns one
    formula per possible value. When several macros are involved, the
    Cartesian product of all of them is generated.
    """
    queue = [formula]
    finalFormulas = []
    iterations = 0

    while queue and iterations < MAX_ITERATIONS:
        currentString = queue.pop(0)
        iterations += 1

        foundKeys = [key for key in macroDict if key in currentString]

        if not foundKeys:
            finalFormulas.append(currentString)
        else:
            # replace longer keys first (?ac before ?a)
            keyToReplace = sorted(foundKeys, key=len, reverse=True)[0]
            for replacementValue in macroDict[keyToReplace]:
                queue.append(currentString.replace(keyToReplace, replacementValue))

    if iterations >= MAX_ITERATIONS:
        print(f"Warning: Reached max iterations ({MAX_ITERATIONS}). Possible unbounded expansion.",
              file=sys.stderr)

    return finalFormulas
