# Auxiliary scripts

Helpers used to prepare the example logs. They are not part of the `dltl`
package; `csv2mod.py` and `ontology_ranges.py` need the optional
dependencies installed with `pip install "semanticdltl[scripts]"`.

| Script | Purpose |
| --- | --- |
| `csv2mod.py <log>` | Convert `<log>.csv` (CaseID, Activity, Timestamp, Actor, ActionType, ModelReference, Details) into `<log>.mod` |
| `mod2nmod.py <model>` | Rewrite `<model>.mod` with one line per trace (`<model>.nmod`) |
| `ontology_ranges.py [file.owl]` | List the datatype properties of an ontology and cast values according to their range |
| `generate_xes_log.py` | Generate a small synthetic XES log |
