# Contributing to SemanticDLTL

Thank you for your interest in SemanticDLTL. Questions, bug reports and
contributions are welcome; this page explains how to make them useful.

## Asking for help

Open an issue on GitHub, or write to semanticdltl@unizar.es. Before asking,
have a look at the [README](README.md) (formula language, commands, output
files), at [examples/](examples/README.md) and, for design questions, at
[docs/architecture.md](docs/architecture.md).

## Reporting a problem

Open an issue with:

- the version (`dltl-mc --version`) and your Python version;
- a **minimal** model that reproduces the problem: a few lines of a `.mod`
  file, with its header;
- the formula or command, exactly as typed, and the propositions file if the
  formula uses `PROP.` or `_LOAD`;
- what you obtained (the printed line, the error and its traceback) and what
  you expected instead.

A report that can be reproduced with `dltl-mc --log-file model --formula-file
formulas.txt --no-interactive` on the attached files is usually fixed quickly.

## Proposing a change

1. Open an issue first for anything beyond a small fix, so that the change
   can be discussed before you invest time in it.
2. Fork the repository and create a branch for the change.
3. Set up the environment and make sure everything passes before you start:

   ```
   make venv      # or: python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
   make check     # ruff + pytest
   ```

4. Make the change, with tests, following the rules below.
5. Open a pull request against `main` describing what changes and why, and
   add an entry to `CHANGELOG.md`.

## Rules for code

- **Every Python file starts with the license header** used by the existing
  files (copy it from any module); `tests/test_headers.py` fails otherwise.
- **`ruff check src tests examples` must pass** with the rules configured in
  `pyproject.toml`, and the whole suite must pass with `pytest`.
- **Behaviour changes need tests.** Unit tests for the module you touch and,
  if the printed results or the `.res`/`.norm`/`.forms` files change, an
  explanation. The reference outputs in `tests/golden/` reproduce the
  original implementation and are updated only for deliberate, documented
  changes: a golden change without a `CHANGELOG.md` entry will not be
  merged.
- **Keep the package free of dependencies.** Anything that needs a
  third-party library (an RDF store, a data-frame library) belongs in a
  propositions module or in `examples/`, behind an optional extra in
  `pyproject.toml`, as the Synthea example does with `pyoxigraph`.
- **Where things go.** New propositions are user code, loaded with
  `--propositions` or `_LOAD`, not additions to the package. A new session
  command is a method of `Session` registered in its command tables. A new
  operator touches three places that must agree: a constructor in
  `formula.py`, a token and a precedence level in `parser.py`, and a handler
  in `evaluator.py`; see [docs/architecture.md](docs/architecture.md),
  section 9.
- Code and documentation are written in English; keep the existing style
  (4-space indentation, lines up to 100 characters, docstrings on public
  functions).

## Documentation

If a change affects users, update the README (command table, formula
syntax, output files) and, when it affects the design, `docs/architecture.md`
and `docs/grammar.md`. Session examples in the documentation show real
output: run them and paste what the tool prints.

## Licensing

SemanticDLTL is distributed under the GNU General Public License v3.0 or
later. By submitting a contribution you agree that it is licensed under the
same terms and that the license header is added to any new file.
