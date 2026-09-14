# Changelog

## 1.1.0 (unreleased)

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

- Partially evaluated formulas are simplified as soon as one of their
  sub-formulas is known, even if freeze variables are still free, and the
  operands of `&` and `|` are substituted in short circuit. Nested freezes
  such as `F(x.(a & F(y.(b & "(x,y)y[T]-x[T]<=120"))))` were quadratic in the
  length of the trace, in time *and* in memory, because the substitution
  rebuilt the whole suffix of the trace once per event; they now cost one data
  expression per pair of events that can satisfy them and stop at the first
  match. On a 5.3-million-event log the formula above went from exhausting the
  memory of the machine (`Killed`) to about a minute; a trace of 2000 events
  went from 39 s and 1.9 GB to 0.01 s and 25 MB. Results are unchanged.
- Data expressions are compiled once and their freeze variables are bound by
  name (the event frozen in `x` is the local name `x` while the expression is
  evaluated) instead of being rewritten textually and `eval`'d as a string at
  every event. A formula with a data expression is 2 to 4 times faster
  (`G(x.("(x)x[Joy] >= 0"))` over 412,000 events: 5.8 s to 1.4 s), and the
  name of a freeze variable may now appear inside string literals of its
  expression (`'x' in x[att]`). A variable must not be called like an
  attribute or like `COL`, `PROP`, `I_POS`, `I_ATOM`.
- Events share their values: identical texts in a column give the same
  object (string, float, frozenset of atoms, `@` frozenset or `$`
  dictionary), the collector is off while a model is loaded and the model is
  frozen afterwards. A 412,000-event log with 17 attributes loads in 1.2 s
  instead of 1.8 s and takes 300 bytes per event instead of 1,150; with the
  smaller heap the checks themselves are 1.5 to 3 times faster. The set of
  atoms of an event (`x[I_ATOM]`) and the `@` attributes are now frozensets,
  and attribute values must not be modified by user propositions.
- The constant nodes `TRUE`/`FALSE` are two shared objects instead of a fresh
  list per event and sub-formula, the simplification at an event returns at
  once for constants and for nodes with free variables, `X`/`Y` shift their
  operand with a slice and the statistics of a trace are one pass. Together
  with the two previous items, over a 412,000-event trace:
  `G(a | b | ... )` with 8 atoms 7.5 s to 0.5 s,
  `F(x.(a & F(y.(b & "..."))))` 4.1 s to 0.6 s, `x.(F(y.("...")))` 9.9 s to 2.1 s,
  `G(x.("(x)x[Joy] >= 0"))` 5.8 s to 0.7 s.
- An error raised by a data expression at an event is reported once per
  distinct message instead of once per event.
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

## 1.0.0

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
