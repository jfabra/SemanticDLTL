# SemanticDLTL — a DLTL model checker

[![License: GPL v3](https://img.shields.io/badge/License-GPL_v3-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![PyPI](https://img.shields.io/pypi/v/semanticdltl.svg)](https://pypi.org/project/semanticdltl/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22777412.svg)](https://doi.org/10.5281/zenodo.22777412)

*SemanticDLTL* checks the traces of an event log against **DLTL** formulas: linear
temporal logic over finite words, extended with **freeze operators** that bind
the data attributes of an event to a variable, so that properties can relate
the attributes of different events of the same trace.

The *semantic* part is what the data attributes can point to: an attribute
can hold the identifier of an event in a knowledge graph, and propositions
written in Python can query that graph (with SPARQL, or any other means)
while the formula is checked. The repository includes a complete example of
this kind, built on synthetic clinical histories generated with
[Synthea](https://github.com/synthetichealth/synthea) and annotated with
SNOMED CT concepts: see [A semantic example](#a-semantic-example-synthea-and-snomed-ct)
below and [examples/synthea/README.md](examples/synthea/README.md).

It implements the algorithm described in

> J. M. Couvreur, J. Ezpeleta.
> [*A Linear Temporal Logic Model Checking Method over Finite Words with
> Correlated Transition Attributes*](https://hal.science/hal-01944569v1).
> Data-Driven Process Discovery and Analysis (SIMPDA 2017), Lecture Notes in
> Business Information Processing, vol. 340, Springer, 2019.

## Installation

Python 3.10 or later, no dependencies. From PyPI:

```
pip install semanticdltl             # the checker
pip install "semanticdltl[synthea]"  # plus pyoxigraph, for the semantic example
```

or from a checkout of this repository:

```
pip install .              # the checker
pip install -e ".[dev]"    # editable, with the test tools (pytest, ruff, build, twine)
pip install ".[synthea]"   # with pyoxigraph, for the semantic example
```

Either way this installs the `dltl` package and the `dltl-mc` command. The
examples and the test-suite are in the repository, not in the PyPI package.

For development on macOS or Linux, `make venv` creates a virtual environment in `.venv/` with
the package installed in editable mode and the development tools; `make test`,
`make lint` and `make sample` run the test-suite, the linter and the checker on
the sample model. The virtual environment is local to each machine and is not
part of the repository. On Windows use the manual commands of the
[Test suite](#test-suite) section instead of the `Makefile`.

This installs the `dltl` package and the `dltl-mc` command. The checker can
also be run without installing, from the repository root, with
`python MC.py` or `python -m dltl` (with `PYTHONPATH=src`).

## Usage

```
dltl-mc --log-file <model> [--init-file FILE] [--formula-file FILE]
        [--no-interactive] [--multi-line] [--propositions FILE.py]
```

| Option | Description | Default |
| --- | --- | --- |
| `--log-file MODEL` | the trace model, with or without the `.mod` suffix; a gzipped `.mod.gz` is accepted | **required** |
| `--init-file FILE` | commands executed before reading formulas (typically macro definitions) | none |
| `--formula-file FILE` | file with the formulas/commands to check | standard input |
| `--interactive` / `--no-interactive` | show the `DLTL -> ` prompt when reading from standard input | interactive |
| `--multi-line` | formulas may span several lines and are terminated by `$` | off |
| `--propositions FILE.py` | Python file whose functions are available as `PROP.<name>` in data expressions | `dltl.propositions` |

The syntax of the original prototype is still accepted:

```
python MC.py log-file=<model> init-file=FILE formula-file=FILE interactive=false multi-line=true
```

Each checked formula prints one line

```
<satisfying traces>,<non-satisfying traces>,<% satisfying>,<seconds>
```

## Running the sample model

`examples/sample.mod` is a tiny model with three traces (`id0`, `id1`,
`id2`) and one attribute of each kind: the atomic proposition `E`, the number
`V`, the set `att` and the dictionary `p`:

```
aE,nV,@att,$p
id0,a&4&a;1&a=1;b=2
id0,a&1&a;1&a=1;b=3
id1,a&4&a;1&a=1;b=2
id1,a&1&a;1&a=1;b=2
id1,b&1&a;2&a=1;b=2
...
id2,b&10&z;input=kkkkkkk;99;Mundo&a=1;b=2
```

### Interactive session

Start the checker on the model and type formulas or commands at the prompt:

```
$ dltl-mc --log-file examples/sample
----------------------------------------
file:      examples/sample.mod
#traces:   3
#events:   17
#atomics:  3
att. desc: ['aE', 'nV', '@att', '$p']
----------------------------------------
DLTL -> F x.("(x)x[V] == 10")
2,1,66.67,0.0
DLTL -> _WHO
id1 id2
DLTL -> G (a | b)
2,1,66.67,0.0
DLTL -> _WHO_NOT
id2
DLTL -> F ((a | b) & z.((X false) & "(z)z[#] == 2"))
1,2,33.33,0.0
DLTL -> _SET ?v 4,10
DLTL -> F x.("(x)x[V] == ?v")
2,1,66.67,0.0
2,1,66.67,0.0
DLTL -> _WRITE
DLTL -> _BYE
```

Reading the session: some event has `V = 10` in two of the three traces
(`_WHO` lists them); every event is `a` or `b` except in `id2`, which contains
`c` and `z` events; only `id0` has exactly two events; the macro `?v` makes the
last formula be checked twice, once per value. `_WRITE` saves the results next
to the model (`examples/sample.res`, `.norm`, `.forms`) and `_BYE` (or
`_AGUR`) ends the session (Ctrl-D also does).

### Batch run

The same can be done non-interactively with an init file, which usually
defines macros, and a formula file:

```
$ dltl-mc --log-file examples/sample --init-file examples/sample.init \
          --formula-file examples/formulas.txt --no-interactive
----------------------------------------
file:      examples/sample.mod
#traces:   3
#events:   17
#atomics:  3
att. desc: ['aE', 'nV', '@att', '$p']
----------------------------------------
0,3,0.0,0.0
1,2,33.33,0.0
3,0,100.0,0.0
...
1,2,33.33,0.0
```

`examples/formulas.txt` contains fourteen formulas (two of them generated by
the macro `?vals`), ends with `_WRITE` and `_BYE`, and therefore leaves in
`examples/`:

```
$ cat examples/sample.res           # one column per formula: holds at the first event?
id0,0,0,1,0,0,0,1,0,1,1,0,0,0,0
id1,0,0,1,0,0,0,1,1,0,0,0,0,0,0
id2,0,1,1,1,1,1,1,0,0,0,1,1,1,1
$ head -2 examples/sample.norm      # fraction of events where each formula holds
id0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,0.0,1.0,1.0,0.0,0.0,0.0,0.0
id1,0.125,0.0,1.0,0.0,0.0,0.0,0.625,0.75,0.0,0.0,0.0,0.0,0.0,0.0
$ head -2 examples/sample.forms     # the formulas, in column order
F a & x.("(x)x[V]==10")
F x.("(x)x[p]['b']==22")
```

With the legacy syntax the batch run reads

```
python MC.py log-file=examples/sample init-file=examples/sample.init formula-file=examples/formulas.txt interactive=false
```

This run is exactly what the regression tests reproduce (see
[Test suite](#test-suite)).

## A semantic example: Synthea and SNOMED CT

`examples/synthea/` contains fourteen event logs (50 to 5000 traces) that
simulate patients going through ten Synthea disease modules (asthma,
allergies, breast and colorectal cancer, COPD, epilepsy, ...). Each event of
a log has, besides its attributes, its own **named graph** in an RDF
knowledge graph (N-Quads) describing the clinical state it executes: SNOMED
CT, LOINC and RxNorm codes with their labels, state type, category, remarks
and observation ranges. The propositions of the example load the graph into
an embedded RDF store ([Oxigraph](https://github.com/oxigraph/oxigraph)) and
ask SPARQL questions inside the graph of the frozen event, so a formula can
say things like "every allergic disposition is eventually followed by an
allergy screening test":

```
G x.("(x)PROP.Allergic_disposition(x[Event])" -> X F y.("(y)PROP.Allergy_screening_test(y[Event])"))
48,2,96.0,0.08
```

The example needs the optional dependency `pyoxigraph`
(`pip install "semanticdltl[synthea]"`). Its README explains the data, the
propositions, a full session step by step, and how to generate new logs:
[examples/synthea/README.md](examples/synthea/README.md).

## Trace model format (`.mod`)

A `.mod` file is a comma-separated text file with one header line describing
the attributes and then one event per line:

```
aE,nV,@att,$p
id0,a&4&a;1&a=1;b=2
id0,a&1&a;1&a=1;b=3
id1,a&4&a;1&a=1;b=5
id1,b&1&h;2&a=1;b=2
```

**Header.** The first character of each field is the attribute type, the rest
its name:

| Type | Attribute |
| --- | --- |
| `a` | atomic proposition: the value is a proposition that holds in the event |
| `s` | string |
| `n` | number (stored as a float) |
| `b` | boolean |
| `@` | set of strings, `item1;item2` |
| `$` | dictionary of `key=value` pairs, `name=John;age=34` (values are cast to bool, float or string) |

Missing values default to `0`, `False` and `''` respectively.

**Events.** `trace_id,value_1&value_2&...`, one value per header field, in
order. Events of the same trace need not be contiguous; traces are sorted by
id.

## Formulas

### Propositions

* **Atomic propositions** are the values of the `a` columns (e.g. `a`, `b`,
  `ac_Start`). They must be identifiers and cannot be `U`, `S`, `X`, `Y`, `G`,
  `H`, `F`, `O`.
* **Data expressions** `"(x,y)<python expression>"` are Python boolean
  expressions over the events frozen in the listed variables (see below).
* `true`, `false`.

### Operators

From the loosest to the tightest binding (see [docs/grammar.md](docs/grammar.md)):

| Syntax | Meaning |
| --- | --- |
| `f -> g`, `f <-> g` | implication, equivalence |
| `f \| g` | or |
| `f & g` | and |
| `f U g` | `f` holds until `g` holds |
| `f S g` | `f` holds since `g` held |
| `F f`, `O f` | eventually / once: `f` holds at some future / past event (including the current one) |
| `Fn f`, `On f` | `f` holds at the current and the next / previous `n-1` events (`F3 f`) |
| `G f`, `H f` | globally / historically: `f` holds at every future / past event |
| `X f`, `Y f` | `f` holds at the next / previous event; false at the last / first event |
| `Xn f`, `Yn f` | `X` / `Y` applied `n` times (`X2 f` is `X X f`) |
| `! f` | not |
| `z.(f)` | **freeze**: bind the current event to variable `z` inside `f` |

Parentheses group sub-formulas. Useful idioms: `X false` holds only at the
last event of a trace and `Y false` only at the first one.

### Freeze operator and data expressions

`z.(f)` binds the current event to the variable `z` (any single lowercase
letter) so that data expressions inside `f` can read its attributes:

```
F x.("(x)x[V] <= 34+7")                       some event has V <= 41
F x.("(x)x[p]['b'] == 22")                    ... has b = 22 in dictionary p
F x.("(x)'z' in x[att]")                      ... contains z in set att
F b & x.(F y.(a & "(x,y)x[V] == y[V]"))       a b-event followed by an a-event with the same V
F ((a | b) & z.((X false) & "(z)z[#] == 2"))  the last event is the 2nd one and is a or b
F x.(b & "(x)PROP.IN_DIC(x[p], 'b', 22)")     using a user-defined proposition
```

Inside a data expression:

* `x[<attr>]` is the value of the non-atomic attribute `<attr>` of the event
  frozen in `x`; `<attr>` is written bare (`x[V]`, not `x['V']`);
* `x[#]` is the position of the event in its trace, starting at 1;
* an event is a tuple `(position, atoms, attr1, attr2, ...)`: `x[I_POS]` is
  its position (the same value as `x[#]`), `x[I_ATOM]` the set of its atomic
  propositions, and `COL['<attr>']` the position of `<attr>` in the tuple;
* `PROP.<name>(...)` calls a function of the propositions module, and
  `<mod>.<name>(...)` one of a module loaded with `_LOAD` (see below);
* any Python expression is allowed (`and`, `or`, `int(...)`, `.get(...)`);
  only numeric attributes can be used in numeric comparisons.

Do not use the name of a freeze variable inside string literals of its
expression (`'x' in x[att]` would be rewritten; use another variable name).

**Security note.** Data expressions are executed with Python's `eval`, files
given to `_LOAD` are imported, and `@` lines are run in the shell. A formula
or init file is therefore as trusted as a Python script: only check files you
would be willing to run.

### User-defined propositions

`src/dltl/propositions.py` is loaded by default as `PROP`. To use your own,
write a Python file and pass it with `--propositions my_props.py`:

```python
COLUMNS = {}   # filled in by the checker: attribute name -> position in the event

def same_actor(x, y):
    return x[COLUMNS['Actor']] == y[COLUMNS['Actor']]
```

```
F x.(X F y.("(x,y)PROP.same_actor(x, y)"))
```

### Loading propositions during a session

Functions can also be added at any moment of a session, without restarting
the checker, with `_LOAD name file.py`; the file becomes available under the
name you choose. `examples/extra_props.py` defines `f(x)` (twice `x`) and
`has_V(event, value)`:

```
DLTL -> F x.("(x)x[V] == 10")
2,1,66.67,0.0
DLTL -> _LOAD mp examples/extra_props.py
DLTL -> F x.("(x)mp.f(x[V]) == 20")
2,1,66.67,0.0
DLTL -> F x.("(x)mp.has_V(x, 4)")
2,1,66.67,0.0
```

Several files can be loaded under different names, and `_LOAD` can go in an
init file so that the functions are available from the start. Loading a name
again replaces the module: edit the file, run `_LOAD` again and the new
definitions are used by the next formula. If the file declares a `COLUMNS`
dictionary it is filled with the attribute positions, as for `PROP`.

The default module provides, among others, `IN_DIC`, `SAME_KEY_VALUE`,
`check_patt` (regular expression on a string attribute), `diff_pos` (distance
between two events) and `has_f_value` (float comparison with tolerance); see
`src/dltl/propositions.py`.

For propositions that query a knowledge graph with SPARQL, see the Synthea
example in `examples/synthea/`: each event of the log has its own named graph
in an RDF store, and the propositions ask questions inside the graph of the
frozen event.

## Commands and macros

Lines starting with `_` are commands, lines starting with `;` are comments,
and a line starting with `@` runs the rest of the line as an operating-system
command (`@ls examples`).

| Command | Effect |
| --- | --- |
| `_INFO` | show information about the loaded model |
| `_SET ?name v1, v2, ...` | define macro `?name` with the given values |
| `_RE ?name <regex>` | define macro `?name` with the atomic propositions matching the regular expression |
| `_RANGE ?name from,to[,step]` | define macro `?name` with a range of integers (inclusive) |
| `_LOAD name file.py` | load a Python file; its functions are used in formulas as `name.<function>` |
| `_WHO` / `_WHO_NOT` | ids of the traces that satisfy / do not satisfy the last checked formula |
| `_WRITE` | save the results (see below) |
| `_WRITE_LENGTHS` | save `<model>_trace_lengths.csv` with the length of each trace |
| `_CLEAR_DATA` (or `_CLEAR_CHECKED`) | forget the checked formulas and their results |
| `_AGUR` or `_BYE` | end the session (`_AGUR` is the historical name, `agur` is also accepted) |

A formula containing macros is checked once per value; with several macros,
once per combination:

```
_SET ?acts ac_Start, ac_End
_RANGE ?n 1,3
F (?acts & X?n ac_Activity)     -> 6 formulas
```

A macro value may itself contain macros, and the resulting formulas keep the
order in which the values were written:

```
DLTL -> _SET ?a a,b
DLTL -> _SET ?b ?a,c
DLTL -> F ?b                     -> F a, F b, F c
2,1,66.67,0.0
2,1,66.67,0.0
1,2,33.33,0.0
```

Macros are expanded only inside formulas: `_SET` does not accept commands.
Commands are recognised before macros are expanded, so `_SET ?bye _AGUR`
followed by `?bye` does not end the session; it checks the formula `_AGUR`
(an atomic proposition that never holds).

`_WRITE` produces, next to the model:

| File | Content |
| --- | --- |
| `<model>.res` | per trace: `id,1,0,1,...`, whether each checked formula holds at its first event |
| `<model>.norm` | per trace: `id,0.5,0.0,...`, the fraction of events where each formula holds |
| `<model>.forms` | the checked formulas, one per line, in the same order as the columns above |

## Using it as a library

```python
from dltl import Log, Session

log = Log.load("examples/sample")
session = Session(log)
for summary in session.check_formula('F x.("(x)x[V] == ?v")'):
    print(summary.formula, summary.yes, summary.no, summary.pct)
session.execute("_WRITE")
```

Lower level, `dltl.parser.parse_formula` builds the formula and
`dltl.evaluator.Evaluator(log.column_index).eval_formula(node, trace)` returns
the value of the formula at every event of a trace.

## Repository layout

```
MC.py               legacy entry point (python MC.py log-file=...)
src/dltl/           the package
  formula.py          formula node constructors
  parser.py           lexer and parser
  evaluator.py        evaluation of formulas over a trace
  log.py              loading of .mod models, saving of results
  macros.py           macro expansion
  session.py          session: results, macros, commands
  propositions.py     default user propositions (PROP)
  cli.py              command line
tests/              pytest suite (tests/golden holds the reference output)
examples/           example models and formulas; examples/synthea is a semantic
                    example with SPARQL-backed propositions (needs pyoxigraph)
docs/grammar.md     formal grammar and operator precedence
docs/architecture.md  technical description of the design and implementation
```

Run the tests with `pytest` and the linter with `ruff check src tests`
(see [Test suite](#test-suite) below).

## Contributing

Bug reports, questions and pull requests are welcome: see
[CONTRIBUTING.md](CONTRIBUTING.md) for how to report a problem usefully and
the rules for code changes.

## Authors and license

SemanticDLTL is developed by Joaquín Ezpeleta and Javier Fabra (Universidad
de Zaragoza, Spain) and María José Ibáñez (Universidad de La Rioja, Spain).
Contact: semanticdltl@unizar.es.

GPL-3.0-or-later. See [LICENSE](LICENSE).

The software is archived on Zenodo: DOI
[10.5281/zenodo.22777412](https://doi.org/10.5281/zenodo.22777412) always
resolves to the latest version, and each release has its own DOI
(1.1.0: [10.5281/zenodo.22777413](https://doi.org/10.5281/zenodo.22777413)).
To cite the tool, use [CITATION.cff](CITATION.cff) (GitHub shows a
"Cite this repository" button with APA and BibTeX); to cite the method,
use the SIMPDA 2017 paper referenced above.

## Test suite

The `tests/` directory contains a pytest suite of 69 test cases, organised in
eight modules. The tests need `pytest` and `ruff`, which are not part of the
standard library, so they are run inside a virtual environment created from
the repository root:

```
python3 -m venv .venv                 # 1. create the environment (once)
source .venv/bin/activate             # 2. activate it (Windows: .venv\Scripts\activate)
pip install -e ".[dev]"               # 3. install the package and the dev tools (once)
pytest                                # 4. run the suite
ruff check src tests                  #    and the linter
```

Once the environment exists, only steps 2 and 4 are needed in later sessions.
The same can be done without activating the environment, by calling the tools
through their path:

```
.venv/bin/pytest
.venv/bin/ruff check src tests
```

or through the `Makefile`, which creates the environment on first use:

```
make test          # pytest
make lint          # ruff
make check         # both
```

Useful pytest options are `-v` (list every test), `tests/test_parser.py`
(one module only) and `-k <expr>` (tests whose name matches an expression).

The suite serves two purposes: it guarantees that the packaged implementation
reproduces the results of the original prototype, and it specifies the
intended behaviour of every component in isolation.

**Regression against the original prototype.** The directory `tests/golden/`
stores the output obtained from the original, unrefactored implementation on
the model `examples/sample.mod` with the init file `examples/sample.init` and
the formulas in `examples/formulas.txt`. Two tests reproduce that session and
compare the summary lines printed for each formula, as well as the files
`.res`, `.norm` and `.forms` produced by `_WRITE`, with the stored reference:
`test_regression_cli.py` invokes the command-line tool with the legacy
`key=value` syntax in a subprocess, whereas `test_regression_api.py` drives
the same session through the `Log` and `Session` classes of the library. A
second, smaller fixture (`examples/sample2.mod` with `examples/formulas2.txt`,
two formulas combining nested freezes with `U` and `H`) is checked the same
way. The API module additionally exercises every session command (`_INFO`,
`_SET`, `_RE`, `_RANGE`, `_LOAD`, `_WHO`, `_WHO_NOT`, `_CLEAR_DATA`,
`_WRITE_LENGTHS`, `_AGUR`/`_BYE`, `@` system calls) and verifies that
a malformed macro name, a missing file in `_LOAD` or a syntactically
incorrect formula is reported without terminating the session. The reference
output was updated deliberately, and only where documented in `CHANGELOG.md`,
for the changes in behaviour introduced in version 1.0.0 (operator precedence
and the removal of the quote escaping in `.forms`).

**Parser** (`test_parser.py`, 13 cases). Construction of atomic propositions
and constants; sharing of a single node among all the occurrences of an
atomic proposition; every unary and binary operator, including implication
and equivalence; expansion of the bounded operators `Xn`, `Yn`, `Fn` and
`On` into nested nodes; operator precedence, in particular that `&` binds
tighter than `|`; left associativity; the freeze operator and data
expressions with one, two or no variables, including the unescaping of quoted
characters; the treatment of the `$` terminator; and the detection of syntax
errors.

**Evaluator** (`test_evaluator.py`, 17 cases). On a hand-built trace of four
events with numeric, set-valued and dictionary-valued attributes, the tests
check the truth value of formulas at every event for each temporal operator
(`X`, `Y`, `F`, `G`, `O`, `H`, `U`, `S` and their bounded versions), the
idioms `X false` and `Y false` identifying the last and first events, the
freeze operator over each attribute type, the event position `x[#]`, the
`COL` map, properties relating two frozen events, the default propositions
module and a user-supplied one relying on `COLUMNS`, the summary statistics
of a trace, the fact that a run-time error inside a data expression is
reported and evaluates to false, the early termination of `F`, `G`, `O` and
`H` once their value is known, and the registration of extra modules for
`_LOAD`.

**Model loading** (`test_log.py`, 11 cases). Loading of the sample model
(number of traces and events, sorted identifiers, atomic propositions,
column index and event tuples); tolerance to the `.mod` suffix; every
attribute type together with its default value when missing; column
numbering when atomic and non-atomic attributes are interleaved;
independence of two models loaded in the same process; rejection of unknown
attribute types, of lines with a wrong number of values and of missing files;
the value casting functions; and the generation of the information text, the
`_WHO`/`_WHO_NOT` answers and the result files.

**Macro expansion** (`test_macros.py`, 7 cases). Formulas without macros,
with a single macro, with several macros (Cartesian product, in order),
nested macros keeping the order of their values, the preference for the
longest matching macro name, and the bounded expansion of cyclic definitions.

**Command line** (`test_cli_args.py`, 8 cases). Translation of the legacy
`key=value` arguments into options, default values, the exit codes returned
when the model is not given (2) or when an input file does not exist (1),
single-line and multi-line (`$`-terminated) reading of formulas, and the
display of the prompt only in interactive mode.
