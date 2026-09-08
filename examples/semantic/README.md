# Semantic event logs

Two synthetic event logs annotated with ontology references, used to
experiment with data-aware properties:

| File | Content |
| --- | --- |
| `WFSemTrazas.csv` | Source log of a flight purchase workflow (SEGITTUR tourism ontology, `segitour.owl`) |
| `WFSemTrazas.mod` | The same log converted with `scripts/csv2mod.py` |
| `WFSemTrazas2.mod` | A remote clinical monitoring workflow annotated with SNOMED CT concepts |
| `formulas.txt` | Formulas to check against `WFSemTrazas.mod` |
| `flight_purchase_log.xes` | Small XES log produced by `scripts/generate_xes_log.py` |

The `.mod` header is

```
aActivity,nTimestamp,aActor,aActionType,sModelReference,$Details
```

so activities, actors and action types are atomic propositions, the timestamp
is numeric, the ontology reference is a string and `Details` is a dictionary
of `key=value` pairs.

Run the checker on it with

```
dltl-mc --log-file examples/semantic/WFSemTrazas --formula-file examples/semantic/formulas.txt --no-interactive
```

## Notes on the CSV

`WFSemTrazas.csv` was cleaned before conversion: in the `Details` column
`"; "` was replaced by `";"`, commas inside values by `-`, and `, /` inside
attribute names by `_`; a repeated header line was removed.
