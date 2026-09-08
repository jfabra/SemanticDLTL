# Changelog

## 1.0.0 (unreleased)

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
