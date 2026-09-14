# Synthea clinical logs: a semantic example

This example shows what the *semantic* part of SemanticDLTL is for. The
logs are synthetic clinical histories generated from
[Synthea](https://github.com/synthetichealth/synthea) disease modules
(asthma, allergies, breast cancer, COPD, ...). Every event of a log has,
besides the attributes stored in the `.mod` file, a small **knowledge
graph** describing the clinical state it executes: its SNOMED CT, LOINC and
RxNorm codes with their labels, its category, remarks, observation ranges.
The graphs live in an RDF store, and the propositions of this example ask
questions about the frozen event with SPARQL, so a DLTL formula can combine
the temporal structure of the trace with knowledge that is not in the log
itself.

| File | Content |
| --- | --- |
| `logs/log_<T>_<min>_<max>.mod` | trace model with `T` traces whose length limit was drawn from `min` to `max` (`.mod.gz` for the large ones; the checker reads them directly) |
| `logs/log_<T>_<min>_<max>.nq` | the knowledge graph of the same log, in N-Quads, one named graph per event |
| `propositions.py` | propositions that query the graph of an event (`PROP.has_code(x[Event], 195967001)`, `PROP.Asthma(x[Event])`, ...) |
| `build_store.py` | loads a `.nq` file into an Oxigraph store, which the propositions read |
| `formulas.txt` | the formulas of the session below, ready for a batch run |
| `generate_logs.py` | the generator: simulates the modules and writes a `.mod` and a `.nq` |
| `workflows/*.json` | the Synthea modules that were simulated |

## The data

### The trace model

`logs/log_50_6_20.mod` has 50 traces (5 per disease module) of at most 20
events: each trace was simulated up to a random limit between 6 and 20
events, or until its module terminated. Its header and first events are:

```
aActivity,nTimestamp,sActor,aActionType,sSnomed,sEvent,aWorkflow
allergies_trace_1,Initial&1783756277&Clinical_System&at_Initial&<http://snomed.info/id/0>&<http://example.org/event/allergies_trace_1_L1>&allergies
allergies_trace_1,Delay_For_Atopy&1783756287&Clinical_System&at_Delay&<http://snomed.info/id/0>&<http://example.org/event/allergies_trace_1_L2>&allergies
```

| Attribute | Type | Meaning |
| --- | --- | --- |
| `Activity` | atomic | name of the Synthea state (`Administer_Allergy_Test`, `Fecal_Test`, ...) |
| `Timestamp` | number | synthetic time, ten seconds between consecutive events |
| `Actor` | string | role that performs the state (`Surgeon`, `Lab_Technician`, `Pharmacist`, ...), derived from keywords of the state |
| `ActionType` | atomic | Synthea state type, prefixed with `at_` (`at_Procedure`, `at_MedicationOrder`, `at_Encounter`, ...) |
| `Snomed` | string | URI of the first SNOMED CT code of the state, `<http://snomed.info/id/0>` if it has none |
| `Event` | string | URI of the event: the name of its graph in the RDF store |
| `Workflow` | atomic | disease module the trace comes from (`allergies`, `copd`, ...) |

`Activity`, `ActionType` and `Workflow` are atomic propositions, so
`Fecal_Test`, `at_Procedure` and `copd` can be used directly in formulas.

### The knowledge graph

`logs/log_50_6_20.nq` describes the same 390 events with 2166 quads. The
fourth element of every quad is the URI of the event, i.e. each event is a
**named graph**. For an allergy screening test the graph contains:

```
<...event/allergies_trace_1_L7> ont:executes      <...procedure/allergies/Administer_Allergy_Test>
<...procedure/.../Administer_Allergy_Test> rdfs:label        "Administer_Allergy_Test"
<...procedure/.../Administer_Allergy_Test> ont:hasStateType  "Procedure"
<...procedure/.../Administer_Allergy_Test> ont:clinicalCode  snomed:395142003
snomed:395142003                            rdfs:label        "Allergy_screening_test"
<...event/allergies_trace_1_L7> ont:follows       <...event/allergies_trace_1_L6>
```

with `ont:` = `http://example.org/ontology/` and `snomed:` =
`http://snomed.info/id/`. The predicates are:

| Predicate | Subject → object |
| --- | --- |
| `ont:hasEvent` | case → event |
| `ont:executes` | event → procedure (the Synthea state) |
| `ont:follows` | event → previous event of the trace |
| `rdfs:label` | procedure → state name; code → display name of the code |
| `ont:hasStateType` | procedure → `Procedure`, `Encounter`, `MedicationOrder`, `ConditionOnset`, ... |
| `ont:hasCategory` | procedure → `laboratory`, `vital-signs`, ... (observations) |
| `ont:clinicalCode` | procedure → SNOMED CT (`snomed:`), LOINC (`http://loinc.org/rdf/`) or RxNorm code |
| `ont:clinicalRemark` | procedure → the remarks of the module author |
| `ont:managesAttribute`, `ont:referencesVariable` | procedure → patient attributes read or written |
| `ont:hasRange`, `ont:hasUnit` | procedure → range and unit of an observation or symptom |

Keeping one graph per event is what makes a proposition *about the frozen
event* a one-line SPARQL query: `ASK { GRAPH <event> { ... } }`.

## Setup

The propositions need [pyoxigraph](https://pypi.org/project/pyoxigraph/),
an embedded RDF store with SPARQL. It is an optional dependency:

```
pip install "semanticdltl[synthea]"
```

Then load the graph of the log you are going to check into a store (a
directory; `store/` next to this README by default):

```
$ python examples/synthea/build_store.py examples/synthea/logs/log_50_6_20.nq
2166 quads loaded into examples/synthea/store
```

`make synthea` does both steps and runs `formulas.txt`. To use a store
somewhere else, point the propositions to it with the environment variable
`SYNTHEA_STORE` or, from Python, with `propositions.set_store(path)`.

## The propositions

`propositions.py` is loaded with `--propositions` (or with `_LOAD`, under a
name of your choice). Every proposition receives the **event URI**, i.e. the
attribute `Event` of the frozen event, and runs an `ASK` inside that graph:

```python
def ask(event, pattern):
    return bool(store.query(f"{PREFIXES} ASK {{ GRAPH {event} {{ {pattern} }} }}"))

def has_code(event, code):            # PROP.has_code(x[Event], 395142003)
    return ask(event, f"?p ont:clinicalCode snomed:{code} .")

def has_state_type(event, t):         # PROP.has_state_type(x[Event], 'Procedure')
    return ask(event, f'?p ont:hasStateType "{t}" .')

def has_category(event, c):           # PROP.has_category(x[Event], 'laboratory')
def label_matches(event, regex):      # PROP.label_matches(x[Event], 'cancer|neoplasm')
def same_code(event1, event2):        # PROP.same_code(x[Event], y[Event])
```

plus one named shortcut per SNOMED CT concept used in the experiments
(`PROP.Asthma`, `PROP.Allergy_screening_test`, `PROP.Surgical_procedure`,
...), each a `has_code` with a fixed code. Adding a proposition is adding a
function with its SPARQL pattern.

## A session, step by step

```
$ dltl-mc --log-file examples/synthea/logs/log_50_6_20 --propositions examples/synthea/propositions.py
----------------------------------------
file:      examples/synthea/logs/log_50_6_20.mod
#traces:   50
#events:   390
#atomics:  107
att. desc: ['aActivity', 'nTimestamp', 'sActor', 'aActionType', 'sSnomed', 'sEvent', 'aWorkflow']
----------------------------------------
```

**Attributes only.** Which traces contain an allergy screening test? The
`.mod` already stores the first SNOMED CT code of each state, so no graph is
needed:

```
DLTL -> F x.("(x)x[Snomed] == '<http://snomed.info/id/395142003>'")
3,47,6.0,0.01
```

(Data expressions cannot contain double quotes, hence the single quotes
around the URI.) Three of the fifty traces.

**The same question through the graph.** `has_code` asks whether the graph
of the event carries the code; the named shortcut is the same query:

```
DLTL -> F x.("(x)PROP.has_code(x[Event], 395142003)")
3,47,6.0,0.05
DLTL -> F x.("(x)PROP.Allergy_screening_test(x[Event])")
3,47,6.0,0.02
```

Same three traces. Likewise, procedures can be found by the log's action
type or by the state type recorded in the graph:

```
DLTL -> F at_Procedure
8,42,16.0,0.0
DLTL -> F x.("(x)PROP.has_state_type(x[Event], 'Procedure')")
8,42,16.0,0.02
```

**Knowledge that is not in the log.** The labels of the codes and the
categories of the observations exist only in the graph:

```
DLTL -> F x.("(x)PROP.label_matches(x[Event], 'cancer|carcinoma|neoplasm')")
4,46,8.0,0.08
DLTL -> _WHO
colorectal_cancer_trace_2 colorectal_cancer_trace_3 colorectal_cancer_trace_4 colorectal_cancer_trace_5
DLTL -> F x.("(x)PROP.has_category(x[Event], 'laboratory')")
2,48,4.0,0.02
```

Four colorectal cancer traces reach a state coded as a neoplasm (the fifth
ends before the diagnosis); two traces contain a laboratory observation.

**Graph propositions combined with log attributes.** Is every procedure
performed by a surgeon?

```
DLTL -> G (x.("(x)PROP.has_state_type(x[Event], 'Procedure')") -> Surgeon)
42,8,84.0,0.05
DLTL -> _WHO_NOT
allergies_trace_1 allergies_trace_3 allergies_trace_5 asthma_trace_3 colorectal_cancer_trace_2 colorectal_cancer_trace_3 colorectal_cancer_trace_4 colorectal_cancer_trace_5
DLTL -> G (Surgeon -> x.("(x)PROP.has_state_type(x[Event], 'Procedure')"))
50,0,100.0,0.13
```

No: in eight traces a procedure (an allergy test, a fecal test) is
performed by a `Lab_Technician`. The converse does hold: surgeons only
appear in procedures.

**Relating two events.** An allergic disposition (SNOMED CT 609328004)
followed, later in the trace, by an allergy screening test; then the same
within one minute of synthetic time (six events, since timestamps are ten
seconds apart); then as an obligation on every allergic disposition:

```
DLTL -> F x.("(x)PROP.Allergic_disposition(x[Event])" & X F y.("(y)PROP.Allergy_screening_test(y[Event])"))
3,47,6.0,0.07
DLTL -> F x.("(x)PROP.Allergic_disposition(x[Event])" & X F y.("(y)PROP.Allergy_screening_test(y[Event])" & "(x,y)y[Timestamp] - x[Timestamp] <= 60"))
3,47,6.0,0.04
DLTL -> G x.("(x)PROP.Allergic_disposition(x[Event])" -> X F y.("(y)PROP.Allergy_screening_test(y[Event])"))
48,2,96.0,0.08
DLTL -> _WHO_NOT
allergies_trace_2 allergies_trace_4
```

The disposition is always followed by the test within a minute when it is
followed at all, and two allergy traces never reach the test. Finally, a
proposition over **two graphs**: a procedure repeated later in the same
trace, i.e. two procedure events whose graphs share a clinical code:

```
DLTL -> F x.(at_Procedure & X F y.(at_Procedure & "(x,y)PROP.same_code(x[Event], y[Event])"))
2,48,4.0,0.14
DLTL -> _WHO
colorectal_cancer_trace_2 colorectal_cancer_trace_4
DLTL -> _BYE
```

## Batch run

The same formulas are in `formulas.txt`, with comments:

```
dltl-mc --log-file examples/synthea/logs/log_50_6_20 --propositions examples/synthea/propositions.py \
        --formula-file examples/synthea/formulas.txt --no-interactive
```

The test-suite runs this file against a store built on the fly and compares
the results with `tests/golden/synthea.stdout` (the test is skipped when
pyoxigraph is not installed).

## The other logs

Fourteen logs were generated for the experiments, with 50, 100, 500, 1000
and 5000 traces and four ranges of trace length. All but the smallest are
gzipped; `--log-file` reads a `.mod.gz` directly and `build_store.py` reads
a `.nq.gz`:

```
python examples/synthea/build_store.py examples/synthea/logs/log_500_21_40.nq.gz mystore
SYNTHEA_STORE=mystore dltl-mc --log-file examples/synthea/logs/log_500_21_40.mod.gz \
        --propositions examples/synthea/propositions.py
```

| Traces | Length limit | Files |
| --- | --- | --- |
| 50 | 6-20, 21-40, 41-60, 61-80 | `log_50_6_20` (plain), `log_50_21_40`, `log_50_41_60`, `log_50_61_80` |
| 100 | 6-20, 21-40, 41-60, 61-80 | `log_100_*` |
| 500 | 6-20, 21-40, 41-60 | `log_500_*` |
| 1000 | 6-20, 21-40 | `log_1000_*` |
| 5000 | 6-20 | `log_5000_6_20` (38 579 events, 213 024 quads) |

Each proposition call is one SPARQL query, so a formula with a semantic
proposition costs one query per event of the log (plus one per pair of
events for `same_code` inside a nested freeze). On the 5000-trace log expect
seconds to minutes per formula.

## Generating new logs

```
python examples/synthea/generate_logs.py --traces 5 --min-steps 6 --max-steps 20 --seed 42
```

simulates every module of `workflows/` (except those that other modules
call as submodules, such as `allergy_panel`) `--traces` times and writes
`logs/log_<T>_<min>_<max>.mod` and `.nq`. A trace starts at the `Initial`
state and follows the module's transitions: direct transitions as they are,
distributed ones by their probabilities, conditional ones by a random
branch (the patient attributes they test are not simulated), until
`Terminal` or the random length drawn from `[min, max]`. The actor of a
state is chosen from keywords in its name, type and category
(`Encounter` → `Practitioner`, `MedicationOrder` → `Pharmacist`, `Procedure`
→ `Surgeon`, ...). With `--seed` the output is reproducible.

## Notes

- Timestamps are synthetic (ten seconds apart) and states without a SNOMED
  CT code get the placeholder `<http://snomed.info/id/0>`.
- The Synthea modules in `workflows/` are from the
  [Synthea project](https://github.com/synthetichealth/synthea) (The MITRE
  Corporation, Apache License 2.0). SNOMED CT codes are used for research
  purposes; SNOMED CT is owned by SNOMED International.
- The store directory is a local artefact (`examples/synthea/store/` is in
  `.gitignore`); rebuild it after changing the log.
