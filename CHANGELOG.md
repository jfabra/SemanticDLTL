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
