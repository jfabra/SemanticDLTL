# Performance notes

This document records the work done on the efficiency of the checker on the
`v2-dev` branch: the workload that motivated it, what was measured, what was
changed and the resulting numbers. The mechanisms themselves are described in
[architecture.md](architecture.md) (sections 4.1, 4.2, 6.1–6.4); this is the
record of *why* and *how much*.

## The workload

The dark patterns study checks formulas such as

```
F(x.(at_RepeatedClick & F(y.(at_ClickBurst & "(x,y)y[Timestamp]-x[Timestamp]<=120"))))
```

against `interactions_emotionsUser.mod`: 860 MB, 17 attributes per event,
15 traces, 5,323,833 events, the longest trace having 1,486,165 events. The
atoms are sparse (in the first 200,000 events: 123,787 `at_Keyboard`, 68,757
`at_Scroll`, 287 `at_RepeatedClick`, 25 `at_ClickBurst`).

The measurements below were taken on a 48 GB Apple silicon machine with
Python 3.14, with `/usr/bin/time -l` (wall time and maximum resident set)
and `cProfile`. Two slices of the log were used for the development loop:

* `t1`: the first trace alone, 412,183 events;
* `burst`: 1,500 events around the first `at_ClickBurst` events, where a
  battery of 23 formulas (future and past operators, `U`/`S`, negations,
  nested freezes, `_WHO`/`_WHO_NOT`) is compared against the previous code
  after every change. All the changes below leave those 23 results, the 79
  tests and the golden files unchanged.

## 1. From quadratic to linear (commit `ac4fc90`)

The original version was killed by the operating system on the log above.
The cause was not memory pressure from the data but the evaluation itself:
while a sub-formula still had free freeze variables it was never simplified,
even when one of its operands was already the constant `False`. With a
nested freeze this meant that

* the disjunction built by the inner `F` kept one node per event, although
  at 99.99 % of them `at_ClickBurst & ...` was already `False`;
* `replace` copied that whole chain once per event of the trace, whether or
  not the event was an `at_RepeatedClick`, and evaluated one data expression
  per copied node.

That is O(n²) in time and, because the copies were all built before being
simplified, in memory alive at once. Measured on slices of the first trace:

| events | time | peak RSS |
| ---: | ---: | ---: |
| 1,000 | 9.1 s | 0.50 GB |
| 2,000 | 39.5 s | 1.94 GB |

i.e. ×4 on doubling. For the 1.5-million-event trace this extrapolates to
~10⁷ s and petabytes.

The fix: the constructors `simp_and`/`simp_or`/`simp_not` fold the constant
cases regardless of free variables; every operator builds its nodes with
them; `replace` folds too and substitutes the operands of `&`/`|` in short
circuit; `eval_fvar` substitutes and simplifies event by event. The number
of data expressions evaluated for the formula above over a 1,500-event
trace with two `a` and one `b` events went from 1,125,750 (= 1500²/2) to 10
(`tests/test_scaling.py` pins this). The same 2,000 events: 0.01 s and
25 MB. The full log: 64 s, 6.5 GB.

## 2. Profiling what was left

After the algorithmic fix, `cProfile` on `t1` showed three things:

| symptom | evidence |
| --- | --- |
| `eval()` on a *string* at every event | 10.1 µs per call against 0.17 µs for a compiled code object (60×); 50–67 % of any formula with a data expression. It could not simply be cached: `replace` rewrote the text (`x` → `THE_TRACE[i]`) so every event produced a different string. |
| every event owned a `set` (216 bytes), its strings and its floats | 1,153 bytes per event. In the real data there are 9 distinct sets of atoms, 298 distinct strings in 1.65 M occurrences and `0.0` is 3.66 M of the 4.95 M floats. The cyclic collector traversed the whole heap during the load and during the checks. |
| constant overhead per event in the evaluator | `eval_formula_in_event` called ~3 times per event, nearly always on nodes it returned untouched, allocating a list and a dict each time (2.9 M calls = 7.8 s of a 16 s pure-LTL formula); `TRUE()`/`FALSE()` copying a list per event (6.5 M copies); `replace` compiling a regex and building four strings per event. |

## 3. The three changes

### `d1a3d98` — data expressions compiled once, variables bound by name

The text of a data expression is compiled once per distinct text (`x[#]` is
rewritten as `x[I_POS]` first) and the events bound so far travel with the
node as a fourth element `{variable: event}`; when no variable is left the
code object is evaluated with those bindings as local namespace. The
regular expression, the rewritten strings and the per-call setup of
`replace` disappear, and a closed expression is evaluated once per trace.

Side effect: since the variable is a local name instead of a textual
substitution, it may now appear inside string literals of its expression
(`'x' in x[att]`); the old limitation is gone from the README and grammar.

### `6b3d883` — shared values in the events, collector kept out of the load

`log._EventBuilder` keeps one cache per column from the raw text of a value
to the parsed value (bounded to 65,536 distinct texts, so a column of unique
values such as a timestamp does not grow it), and one cache for the set of
atoms. Events that spell a value identically share the object; atoms and
`@` attributes are frozensets. `Log.load` disables the cyclic collector
while it allocates millions of long-lived containers and calls `gc.freeze()`
afterwards, so the collections triggered by the short-lived nodes of the
checks do not traverse the model.

### `eaa81a8` — shared constant nodes, cheap common cases

`TRUE_VAL` and `FALSE_VAL` are the only constant nodes (no node is ever
modified in place) and `is_true`/`is_false` test identity first;
`eval_formula_in_event` answers constants and nodes with free variables
before allocating; `results_statistics` is one pass; `X`/`Y` shift with a
slice; an error raised by a data expression is reported once per message.

## 4. Results

### First trace (`t1`, 412,183 events), one process per stage

| | original | after 1 | after 2 | after 3 | overall |
| --- | ---: | ---: | ---: | ---: | ---: |
| load | 1.82 s | 1.84 s | 1.20 s | 1.05 s | 1.7× |
| bytes per event | 1,153 | 1,153 | 299 | 296 | 3.9× |
| `F(x.(at_RepeatedClick & F(y.(at_ClickBurst & "…<=120"))))` | 4.09 s | 3.23 s | 1.54 s | 0.63 s | 6.5× |
| `x.(F(y.("(x,y)y[Timestamp]-x[Timestamp]>=0")))` | 9.91 s | 4.89 s | 2.94 s | 2.06 s | 4.8× |
| `G(at_Scroll \| at_Keyboard \| … )` (8 atoms, no data) | 7.54 s | 8.24 s | 2.63 s | 0.54 s | 14× |
| `G(x.("(x)x[Joy] >= 0.0"))` | 5.83 s | 1.41 s | 1.01 s | 0.68 s | 8.6× |
| peak RSS of the run | 828 MB | 868 MB | 527 MB | 495 MB | 1.7× |

("original" is `ac4fc90`, i.e. already linear; the pure-LTL formula gains
most from stage 2 because its millions of short-lived nodes no longer make
the collector traverse the model.)

### Full log (15 traces, 5,323,833 events), one session with three formulas

| | `ac4fc90` | `eaa81a8` | |
| --- | ---: | ---: | ---: |
| `F(x.(at_RepeatedClick & F(y.(at_ClickBurst & "…<=120"))))` | 65.5 s | 8.1 s | 8× |
| `x.(F(y.("(x,y)y[Timestamp]-x[Timestamp]>=0")))` | 143.3 s | 28.4 s | 5× |
| `G(x.(at_RepeatedClick -> F(y.(at_ClickBurst & "…<=120"))))` | 101.1 s | 9.0 s | 11× |
| whole session (load + 3 formulas) | 356 s | 60 s | 6× |
| peak RSS | 7.3 GB | 2.8 GB | 2.6× |

Results: `10,5,66.67`, `15,0,100.0`, `2,13,13.33`, identical before and after.

## 5. What remains

* A nested freeze whose data expression is false for most pairs of events
  still scans the suffix of the trace for every frozen event; the folding
  and the short circuit reduce the work to the events that can satisfy the
  formula, not below (architecture.md, section 12).
* Traces are independent, so the checks could run in several processes;
  the loaded model would have to be shared or loaded per process.
* `Session` accumulates the per-trace results as strings (`+=` per formula);
  this is only noticeable with thousands of formulas produced by macros and
  was left as is because `Session.results` is part of the public API.

## Reproducing the measurements

```
# slices of the real log (the log itself is not in the repository)
{ head -1 interactions_emotionsUser.mod; sed -n '2,412184p' interactions_emotionsUser.mod; } > t1.mod

# time and memory of one session
/usr/bin/time -l dltl-mc --log-file t1 --formula-file formulas.txt --no-interactive

# where the time goes
python -c "import cProfile, pstats; from dltl import Log, Session; \
  s = Session(Log.load('t1')); \
  cProfile.run('s.check_formula(open(\"formulas.txt\").readline())', 'prof'); \
  pstats.Stats('prof').sort_stats('tottime').print_stats(15)"
```

`tests/test_scaling.py` counts the data expressions evaluated by the freeze
formulas and fails if the quadratic behaviour ever comes back.
