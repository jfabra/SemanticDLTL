# Changelog

## 1.2.0 (2026-11-06)

Archived on Zenodo (DOI 10.5281/zenodo.23991412).

### New

- XES event logs (`.xes`, or gzipped `.xes.gz`) are read directly:
  `dltl-mc --log-file log.xes`, `Log.load("log.xes")` or
  `dltl.load_xes(path, schema=..., trace_id_key=..., ignore=...)`. No `.mod`
  file is written. By default `concept:name` is an atomic
  proposition and the other attributes of the events get a type from their
  XES type; `--xes-schema FILE.xml` gives types and names with a `mod:schema`
  container, `--xes-ignore` loads only the attributes that appear in it and
  `--xes-trace-id-key` chooses the trace identifier. Result files are written
  next to the log.
- `Log.from_rows` builds a model from header fields and raw event values; it
  is the constructor shared by the `.mod` and XES loaders.
- `examples/sample.xes` and `examples/sample.schema.xml`: the sample model as
  an XES log.
- `examples/xes-example/`: a real XES log, that of the Conformance Checking
  Challenge 2019 (20 recorded procedures of central venous catheter
  installation, 1394 events; CC BY 4.0), with a mapping schema, formulas and a
  documented session. `make xes-example` runs it.
- `examples/synthea/benchmark/`: the 50 benchmark formulas over the Synthea
  logs, each followed by `_WHO`, with the output of checking them on eight
  logs (50 to 100 000 traces of 6 to 20 events, and 10 000 traces in the four
  ranges of trace length). `make synthea-benchmark` runs them on the small
  log.
- Six larger logs in `examples/synthea/logs` (`.mod.gz` and `.nq.gz`):
  `log_10000_6_20`, `log_10000_21_40`, `log_10000_41_60`, `log_10000_61_80`,
  `log_50000_6_20` and `log_100000_6_20` (up to 648 926 events), generated
  with `generate_logs.py --seed 42 --base-time 1700000000`.

### Changed

- An empty value of a dictionary attribute (`$`) in a `.mod` file is an empty
  dictionary, as before, but no longer prints "Error processing dictionary
  attribute values".
- `Log` has a new field `source`, the file the model was read from when it is
  not `<path>.mod`; `_INFO` shows it.

## 1.1.0 (2026-09-15)

First release on PyPI (`pip install semanticdltl`) and on Zenodo
(DOI 10.5281/zenodo.22777413).

Port of the second version of the prototype (the one that was actually meant
to be published) onto the packaged code base.

### New

- `_LOAD name file.py` loads a Python file during a session; its functions
  and variables are available in data expressions as `name.<attribute>`.
- Lines starting with `@` run the rest of the line in the operating-system
  shell.
- `_BYE` ends the session, as an alternative to the historical `_AGUR`
  (`agur` is also accepted).
- Events now carry their position in the trace: an event is the tuple
  `(position, atoms, attr1, attr2, ...)`, with `I_POS = 0` and `I_ATOM = 1`
  exported by `dltl.log` and available inside data expressions. `x[#]` keeps
  working and equals `x[I_POS]`. Non-atomic attributes therefore start at
  index 2 (`Log.column_index` reflects it; code that used hard-coded
  positions must be adjusted).
- `F`, `G`, `O` and `H` stop evaluating a trace as soon as their value is
  known for the remaining events (same results, less work).
- A non-numeric value in a numeric column produces a warning and `0.0`
  instead of aborting the load.
- Default propositions module aligned with the prototype: `IN_DIC`,
  `IN_DIC_2`, `SAME_KEY_VALUE`, `check_patt`, `check_patt_f`,
  `diff_att_geq`, `diff_pos`, `has_f_value`, `near`, `quote` (the last three
  were broken in the prototype and are fixed). `suma`, `doble`, `TS_IG` and
  the SPARQL helpers are gone.
- Second regression fixture `examples/sample2.mod` + `examples/formulas2.txt`.
- `examples/synthea/`: a semantic example with fourteen clinical event logs
  generated from Synthea disease modules (50 to 5000 traces), each paired
  with an RDF knowledge graph in N-Quads (one named graph per event), a
  propositions module that queries the graph of the frozen event with SPARQL
  through Oxigraph, the log generator, a store builder and a documented
  session. Optional dependency `pyoxigraph` (`pip install "semanticdltl[synthea]"`).
- `Log.load` (and `--log-file`) accept gzipped models (`model.mod.gz`).
- Nested macros are expanded depth-first, so the generated formulas keep the
  order of the macro values (`?a` = `a,b`, `?b` = `?a,c` gives `a, b, c`;
  the prototype gave `c, a, b`). Macro values are never interpreted as
  commands; this is now documented.

### Changed

- The trace lengths file is `<model>_trace_lengths.csv` (was `.txt`).
- `examples/sample.mod` is the prototype's updated model (trace `id2` has `c`
  events); one column of the reference `.norm` changed accordingly.
- Loading time is printed only in interactive mode.

### Removed

- The `scripts/` directory (log conversion helpers) and the semantic event
  logs of `examples/semantic/`.

### Not ported

- The prototype's experimental parallel entry point (`MC_multi_proc.py`,
  based on `pathos`) is not included: it did not run against the prototype's
  own evaluator. Parallel evaluation of traces is left as future work.

## 1.0.0 (2026-09-02)

First packaged release of the model checker, now called SemanticDLTL
(importable as `dltl`, command `dltl-mc`, `python -m dltl` or the legacy
`python MC.py`).

### Behaviour changes with respect to the prototype

- **Operator precedence**: `&` now binds tighter than `|`, as stated in the
  grammar and as is conventional. `a | b & c` is read as `a | (b & c)`; the
  prototype read it as `(a | b) & c`. Use parentheses if you relied on the old
  reading.
- `_WHO_NOT` is dispatched as a command (it used to be parsed as a formula).
- `_CLEAR_DATA` (alias `_CLEAR_CHECKED`) also forgets the list of checked
  formulas, so `.forms` and `.res` stay aligned.
- The trace lengths file is no longer written every time a model is loaded:
  the new `_WRITE_LENGTHS` command writes it on demand, and it is now called
  `<log>_trace_lengths.txt` (it was `<log>_longs_trazas.txt`).
- Formulas are saved in `.forms` exactly as typed (the prototype leaked a
  `\'` escaping into the file).
- Missing init/formula files stop the run with exit code 1 instead of
  silently falling back to the standard input.
- Attribute names that collide with evaluator internals (`t`, `v`, `X`, ...)
  and atomic propositions that are not valid Python identifiers now work.
- Several models can be loaded in the same process (`Log.load`).

### Command line

- New `--key value` options (`--log-file`, `--init-file`, `--formula-file`,
  `--no-interactive`, `--multi-line`, `--propositions`, `--version`); the
  `key=value` syntax is still accepted.
