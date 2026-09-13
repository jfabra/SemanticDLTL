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
Semantic propositions for the Synthea example: SPARQL queries over the
knowledge graph of a log, evaluated per event.

Every quad of ``log_*.nq`` is stored in the named graph of the event it
describes, so a proposition about the event frozen in ``x`` asks its question
*inside that graph*::

    ASK { GRAPH <http://example.org/event/asthma_trace_3_L7> { ... } }

The event URI is the value of the ``Event`` attribute of the model, hence the
propositions are used as ``PROP.has_code(x[Event], 195967001)`` or, with the
named shortcuts, ``PROP.Asthma(x[Event])``.

The graph is read from an Oxigraph store built with ``build_store.py``. Its
directory is taken from the ``SYNTHEA_STORE`` environment variable or, by
default, ``store/`` next to this file; ``set_store(path)`` overrides it.

Requires ``pyoxigraph`` (``pip install "semanticdltl[synthea]"``).
"""
from __future__ import annotations

import os
from pathlib import Path

PREFIXES = """PREFIX snomed: <http://snomed.info/id/>
PREFIX ont: <http://example.org/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

_store = None
_store_dir: str | None = os.environ.get("SYNTHEA_STORE")


def set_store(path: str | os.PathLike) -> None:
    """Use the Oxigraph store at ``path`` (must have been built with ``build_store.py``)."""
    global _store, _store_dir
    _store_dir = str(path)
    _store = None


def _get_store():
    global _store
    if _store is None:
        try:
            from pyoxigraph import Store
        except ImportError as e:
            raise ImportError("the Synthea propositions need pyoxigraph: "
                              'pip install "semanticdltl[synthea]"') from e
        path = _store_dir or str(Path(__file__).resolve().parent / "store")
        if not Path(path).is_dir():
            raise FileNotFoundError(f"Oxigraph store '{path}' not found; build it with "
                                    "build_store.py or point SYNTHEA_STORE to it")
        _store = Store(path)
    return _store


def ask(event: str, pattern: str) -> bool:
    """``ASK`` whether ``pattern`` (a SPARQL group pattern) holds in the graph of ``event``."""
    query = f"{PREFIXES} ASK {{ GRAPH {event} {{ {pattern} }} }}"
    return bool(_get_store().query(query))


# --- generic propositions ---------------------------------------------------

def has_code(event: str, code: int | str) -> bool:
    """The event carries the SNOMED CT concept ``code``."""
    return ask(event, f"?p ont:clinicalCode snomed:{code} .")


def has_state_type(event: str, state_type: str) -> bool:
    """The Synthea state executed by the event is of type ``state_type`` (``Procedure``, ...)."""
    return ask(event, f'?p ont:hasStateType "{state_type}" .')


def has_category(event: str, category: str) -> bool:
    """The state has the given ``category`` (``vital-signs``, ``laboratory``, ...)."""
    return ask(event, f'?p ont:hasCategory "{category}" .')


def label_matches(event: str, regex: str) -> bool:
    """Some clinical code of the event has a label matching ``regex`` (case-insensitive)."""
    return ask(event, f'?p ont:clinicalCode ?c . ?c rdfs:label ?l . '
                      f'FILTER regex(?l, "{regex}", "i")')


def same_code(event1: str, event2: str) -> bool:
    """Both events carry a common clinical code."""
    query = (f"{PREFIXES} ASK {{ GRAPH {event1} {{ ?p1 ont:clinicalCode ?c . }} "
             f"GRAPH {event2} {{ ?p2 ont:clinicalCode ?c . }} }}")
    return bool(_get_store().query(query))


# --- named SNOMED CT concepts ----------------------------------------------

def Asthma(event): return has_code(event, 195967001)
def Inhaled_steroid_therapy(event): return has_code(event, 710818004)
def Gynecology_service(event): return has_code(event, 310061009)
def Smoking_cessation_therapy(event): return has_code(event, 710081004)
def Atopic_dermatitis(event): return has_code(event, 24079001)
def Administration_of_intravenous_fluids(event): return has_code(event, 103744005)
def Malignant_neoplasm_of_breast(event): return has_code(event, 254837009)
def Allergic_disposition(event): return has_code(event, 609328004)
def Allergy_screening_test(event): return has_code(event, 395142003)
def Asthma_screening(event): return has_code(event, 171231001)
def Contact_dermatitis(event): return has_code(event, 40275004)
def Chronic_obstructive_bronchitis(event): return has_code(event, 185086009)
def Malignant_neoplasm_of_colon(event): return has_code(event, 93761005)
def Surgical_procedure(event): return has_code(event, 73761001)
def Therapeutic_procedure(event): return has_code(event, 737567002)
