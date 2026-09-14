#!/usr/bin/env python3
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
Generate synthetic clinical event logs by simulating Synthea disease modules.

    python generate_logs.py --traces 5 --min-steps 6 --max-steps 20 --seed 42

For every module in ``workflows/`` the script walks its state machine
``--traces`` times, choosing among the outgoing transitions at random, and
writes two files to ``logs/``:

* ``log_<T>_<min>_<max>.mod``: the trace model for SemanticDLTL, one event
  per line with the attributes ``Activity`` (state name), ``Timestamp``,
  ``Actor``, ``ActionType`` (state type), ``Snomed`` (URI of the first SNOMED
  CT code of the state), ``Event`` (URI of the event) and ``Workflow``;
* ``log_<T>_<min>_<max>.nq``: the knowledge graph in N-Quads, one named graph
  per event, describing the state executed by the event: its type, category,
  remarks, every clinical code (SNOMED CT, LOINC, RxNorm) with its label, the
  attributes it manages, observation ranges, and the previous event.

``T`` is the total number of traces. Modules that other modules call as
submodules (``allergy_panel``) are not simulated on their own unless
``--include-submodules`` is given. With ``--seed`` the output is reproducible
(the timestamps start at ``--base-time``).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOD_HEADER = "aActivity,nTimestamp,sActor,aActionType,sSnomed,sEvent,aWorkflow"

# keyword rules deciding the actor of a state, applied in order
ACTOR_RULES = [
    (("WELLNESS",), "Primary_Care_Physician"),
    (("EMERGENCY", "ED_VISIT", "TRIAGE"), "ER_Staff"),
    (("ENCOUNTER", "CONSULTATION", "VISIT", "SUBMODULE"), "Practitioner"),
    (("CONDITION", "SYMPTOM", "DIAGNOSIS", "ONSET"), "Physician"),
    (("MEDICATION", "PRESCRIPTION", "DRUG", "RX", "IMMUNIZATION"), "Pharmacist"),
    (("OBSERVATION", "LAB", "VITAL", "BLOOD", "URINE", "PANEL", "TEST", "EEG"), "Lab_Technician"),
    (("PROCEDURE", "SURGERY", "BIOPSY", "EXCISION"), "Surgeon"),
    (("IMAGING", "XRAY", "SCAN", "MRI", "CT", "MAMMOGRAM", "ULTRASOUND"), "Radiologist"),
    (("CAREPLAN", "PLAN"), "Care_Manager"),
    (("DEATH",), "Medical_Examiner"),
]
DEFAULT_ACTOR = "Clinical_System"


# --- helpers -----------------------------------------------------------------

def clean(txt) -> str:
    return str(txt).replace(" ", "_").replace('"', "").replace("'", "").replace("\n", " ")


def quad(s: str, p: str, o: str, g: str) -> str:
    return f"{s} {p} {o} {g} ."


def literal(txt) -> str:
    return f'"{clean(txt)}"'


def code_uri(system: str, code: str) -> str:
    system = system.upper()
    if "SNOMED" in system:
        return f"<http://snomed.info/id/{code}>"
    if "LOINC" in system:
        return f"<http://loinc.org/rdf/{code}>"
    if "RXNORM" in system:
        return f"<http://rxnav.nlm.nih.gov/REST/rxcui/{code}>"
    return f"<http://example.org/code/{clean(system)}/{code}>"


def all_codes(data) -> list[dict]:
    """Every ``{"system": ..., "code": ...}`` dictionary nested anywhere in ``data``."""
    found = []
    if isinstance(data, dict):
        if "code" in data and "system" in data:
            found.append(data)
        for value in data.values():
            found.extend(all_codes(value))
    elif isinstance(data, list):
        for item in data:
            found.extend(all_codes(item))
    return found


def first_snomed(state: dict) -> str:
    """Code of the first SNOMED CT concept of the state, ``'0'`` if it has none."""
    candidates = list(state.get("codes", []))
    if "value_code" in state:
        candidates.append(state["value_code"])
    if "discharge_disposition" in state:
        candidates.append(state["discharge_disposition"])
    for activity in state.get("activities", []):
        candidates.extend(activity.get("codes", []))
    for c in candidates:
        if isinstance(c, dict) and "SNOMED" in str(c.get("system", "")).upper():
            return str(c.get("code", "0"))
    return "0"


def actor_of(state_name: str, state: dict) -> str:
    target = f"{state.get('type', '')} {state_name} {state.get('category', '')}".upper()
    if state.get("wellness"):
        return "Primary_Care_Physician"
    for keywords, actor in ACTOR_RULES:
        if any(k in target for k in keywords):
            return actor
    return DEFAULT_ACTOR


def next_state(state: dict, rng: random.Random) -> str | None:
    if "direct_transition" in state:
        return state["direct_transition"]
    if "distributed_transition" in state:
        dist = state["distributed_transition"]
        return rng.choices([d["transition"] for d in dist],
                           weights=[d.get("distribution", 0) for d in dist])[0]
    if "complex_transition" in state:
        for entry in state["complex_transition"]:
            if "distributions" in entry:
                dist = entry["distributions"]
                return rng.choices([d["transition"] for d in dist],
                                   weights=[d.get("distribution", 0) for d in dist])[0]
            if "transition" in entry:
                return entry["transition"]
    if "conditional_transition" in state:
        # the conditions refer to patient attributes we do not simulate: pick one at random
        return rng.choice(state["conditional_transition"])["transition"]
    if state.get("type") == "CallSubmodule":
        return "Terminal"
    return None


def state_semantics(state_name: str, state: dict, event_uri: str, wf_name: str) -> list[str]:
    """Quads describing the state executed by ``event_uri``, in its named graph."""
    proc = f"<http://example.org/procedure/{wf_name}/{clean(state_name)}>"
    q = [quad(proc, "<http://www.w3.org/2000/01/rdf-schema#label>", literal(state_name), event_uri),
         quad(proc, "<http://example.org/ontology/hasStateType>",
              literal(state.get("type", "State")), event_uri)]
    if "category" in state:
        q.append(quad(proc, "<http://example.org/ontology/hasCategory>", literal(state["category"]),
                      event_uri))
    remarks = state.get("remarks", [])
    if isinstance(remarks, list) and " ".join(remarks).strip():
        q.append(quad(proc, "<http://example.org/ontology/clinicalRemark>",
                      literal(" ".join(remarks)), event_uri))
    seen = set()
    for c in all_codes(state):
        uri = code_uri(str(c.get("system", "unknown")), clean(c.get("code", "0")))
        if uri in seen:
            continue
        seen.add(uri)
        q.append(quad(proc, "<http://example.org/ontology/clinicalCode>", uri, event_uri))
        q.append(quad(uri, "<http://www.w3.org/2000/01/rdf-schema#label>",
                      literal(c.get("display", "N/A")), event_uri))
    attribute = state.get("assign_to_attribute") or state.get("attribute")
    if attribute:
        q.append(quad(proc, "<http://example.org/ontology/managesAttribute>", literal(attribute),
                      event_uri))
    if "range" in state:
        r = state["range"]
        q.append(quad(proc, "<http://example.org/ontology/hasRange>",
                      literal(f"{r.get('low', '0')}-{r.get('high', '0')}"), event_uri))
        q.append(quad(proc, "<http://example.org/ontology/hasUnit>",
                      literal(state.get("unit", "score")), event_uri))
    for field in ("careplan", "medication_order", "referenced_by_attribute"):
        if field in state:
            q.append(quad(proc, "<http://example.org/ontology/referencesVariable>",
                          literal(state[field]), event_uri))
    return q


# --- simulation --------------------------------------------------------------

def simulate_trace(wf_name: str, states: dict, trace_id: str, max_steps: int,
                   base_time: int, rng: random.Random) -> tuple[list[str], list[str]]:
    """Walk the module from ``Initial``; returns the .mod lines and the quads of one trace."""
    mod, nq = [], []
    case_uri = f"<http://example.org/case/{trace_id}>"
    current, line_id, steps = "Initial", 1, 0
    while steps < max_steps and current in states:
        state = states[current]
        event_uri = f"<http://example.org/event/{trace_id}_L{line_id}>"
        proc_uri = f"<http://example.org/procedure/{wf_name}/{clean(current)}>"
        timestamp = base_time + line_id * 10
        snomed = f"<http://snomed.info/id/{first_snomed(state)}>"
        mod.append(f"{trace_id},{clean(current)}&{timestamp}&{actor_of(current, state)}"
                   f"&at_{clean(state.get('type', ''))}&{snomed}&{event_uri}&{wf_name}")
        nq.append(quad(case_uri, "<http://example.org/ontology/hasEvent>", event_uri, event_uri))
        nq.append(quad(event_uri, "<http://example.org/ontology/executes>", proc_uri, event_uri))
        nq.extend(state_semantics(current, state, event_uri, wf_name))
        if line_id > 1:
            previous = f"<http://example.org/event/{trace_id}_L{line_id - 1}>"
            nq.append(quad(event_uri, "<http://example.org/ontology/follows>", previous, event_uri))
        following = next_state(state, rng)
        if not following or following == "Terminal" or following not in states:
            break
        current, line_id, steps = following, line_id + 1, steps + 1
    return mod, nq


def submodules_of(workflows: list[Path]) -> set[str]:
    """Names of the modules that are called as submodules by any of ``workflows``."""
    names = set()
    for wf_path in workflows:
        for state in json.loads(wf_path.read_text(encoding="utf-8"))["states"].values():
            if "submodule" in state:
                names.add(str(state["submodule"]).rsplit("/", 1)[-1])
    return names


def generate(workflows: list[Path], out_dir: Path, traces: int, min_steps: int, max_steps: int,
             seed: int | None, base_time: int) -> tuple[Path, Path]:
    rng = random.Random(seed)
    mod_lines, nq_lines = [MOD_HEADER], []
    for wf_path in workflows:
        wf_name = wf_path.stem
        states = json.loads(wf_path.read_text(encoding="utf-8"))["states"]
        for i in range(traces):
            limit = rng.randint(min_steps, max_steps)
            mod, nq = simulate_trace(wf_name, states, f"{wf_name}_trace_{i + 1}", limit,
                                     base_time, rng)
            mod_lines.extend(mod)
            nq_lines.extend(nq)
    base = f"log_{traces * len(workflows)}_{min_steps}_{max_steps}"
    out_dir.mkdir(parents=True, exist_ok=True)
    mod_path, nq_path = out_dir / f"{base}.mod", out_dir / f"{base}.nq"
    mod_path.write_text("\n".join(mod_lines) + "\n", encoding="utf-8")
    nq_path.write_text("\n".join(nq_lines) + "\n", encoding="utf-8")
    return mod_path, nq_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--workflows-dir", default=str(HERE / "workflows"),
                        help="directory with the Synthea module JSON files")
    parser.add_argument("--out-dir", default=str(HERE / "logs"))
    parser.add_argument("--traces", type=int, default=5, help="traces per module (default 5)")
    parser.add_argument("--min-steps", type=int, default=6)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=None, help="seed for a reproducible log")
    parser.add_argument("--base-time", type=int, default=None,
                        help="first timestamp, seconds since the epoch (default: now)")
    parser.add_argument("--include-submodules", action="store_true",
                        help="also simulate the modules that others call as submodules")
    args = parser.parse_args(argv)

    workflows = sorted(Path(args.workflows_dir).glob("*.json"))
    if not args.include_submodules:
        subs = submodules_of(workflows)
        workflows = [w for w in workflows if w.stem not in subs]
    if not workflows:
        print(f"Error: no .json modules in '{args.workflows_dir}'", file=sys.stderr)
        return 1
    if args.min_steps < 1 or args.max_steps < args.min_steps:
        print("Error: need 1 <= --min-steps <= --max-steps", file=sys.stderr)
        return 1
    base_time = args.base_time if args.base_time is not None else int(time.time())
    mod_path, nq_path = generate(workflows, Path(args.out_dir), args.traces, args.min_steps,
                                 args.max_steps, args.seed, base_time)
    print(f"{len(workflows)} modules x {args.traces} traces -> {mod_path} and {nq_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
