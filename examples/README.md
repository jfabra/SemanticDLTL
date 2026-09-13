# Examples

| File | Content |
| --- | --- |
| `sample.mod` | Tiny model with three traces and one attribute of each type (used by the tests) |
| `sample.init` | Init file defining two macros with `_SET` |
| `formulas.txt` | Formulas exercising the freeze operator, data expressions, macros, `_WRITE` and `_BYE` |
| `sample2.mod` | Four traces with an extra string attribute `Extra` |
| `formulas2.txt` | Two formulas on `sample2` combining nested freezes with `U` and `H` |
| `extra_props.py` | Propositions to load during a session with `_LOAD` (see below) |
| `session_macros.txt` | A session showing `_SET`, `_RE` and `_RANGE` macros |

Run the small example non-interactively:

```
dltl-mc --log-file examples/sample --init-file examples/sample.init \
        --formula-file examples/formulas.txt --no-interactive
dltl-mc --log-file examples/sample2 --formula-file examples/formulas2.txt --no-interactive
```

or start an interactive session on it:

```
dltl-mc --log-file examples/sample
DLTL -> F x.("(x)x[V] == 10")
2,1,66.67,0.0
DLTL -> _WHO
id1 id2
DLTL -> _BYE
```

## Loading your own propositions with `_LOAD`

Data expressions can call any Python function. The functions of the default
module are available as `PROP.<name>`, but often you need one that does not
exist yet, in the middle of a session, without restarting the checker. That
is what `_LOAD` is for:

```
_LOAD <name> <file.py>
```

reads a Python file and makes everything it defines available in formulas as
`<name>.<function>`. The name is yours to choose; it only has to be a valid
Python identifier.

### The file

`extra_props.py` is a minimal example. Stripped of its license header it is:

```python
COLUMNS: dict[str, int] = {}

C = 1

def f(x):
    """Twice ``x``."""
    return 2 * x

def has_V(event, value):
    """The event has attribute ``V`` equal to ``value``."""
    return event[COLUMNS['V']] == value
```

Three things to notice:

- `f` works on a plain value: it will receive the attribute you pass it
  (`mp.f(x[V])`).
- `has_V` works on a **whole event**: it will receive the frozen event
  itself (`mp.has_V(x, 4)`) and looks the attribute up by name through
  `COLUMNS`. An event is a tuple, and `COLUMNS` maps each attribute name to
  its position in it; the checker fills this dictionary when the file is
  loaded, so the function does not need to know the layout of the model.
  Declaring `COLUMNS` is optional: a file whose functions only take values
  does not need it.
- `C` shows that variables are exported too (`mp.C`).

### A session, step by step

The sample model has three traces: in `id0` and `id1` the first event has
`V = 4`, in `id1` and `id2` some event has `V = 10`.

```
$ dltl-mc --log-file examples/sample
DLTL -> F x.("(x)x[V] == 10")
2,1,66.67,0.0
```

Two traces contain an event with `V = 10`. Now suppose we want to express
"an event whose *doubled* `V` is 20" through a function. Load the file:

```
DLTL -> _LOAD mp examples/extra_props.py
```

Nothing is printed: the session simply goes on, with a new name `mp` in
scope. From now on every formula can use it:

```
DLTL -> F x.("(x)mp.f(x[V]) == 20")
2,1,66.67,0.0
```

Same two traces as before, as expected, since `mp.f` doubles its argument.
A function receiving the whole event:

```
DLTL -> F x.("(x)mp.has_V(x, 4)")
2,1,66.67,0.0
```

`id0` and `id1` start with `V = 4`; `id2` never has it. Variables and
functions can be mixed freely with the rest of the formula language:

```
DLTL -> F x.("(x)mp.f(x[V]) == mp.C * 8")
2,1,66.67,0.0
DLTL -> F x.(b & "(x)mp.has_V(x, 10)")
1,2,33.33,0.0
DLTL -> _WHO
id2
```

The last formula asks for a `b` event with `V = 10`: only the final event of
`id2` (`b&10&...`) qualifies.

### Editing and reloading

Loading a name that is already in use **replaces** the module, so you can
edit the file and pick up the change without leaving the session. Copy the
example, change `has_V` so that it checks `>=` instead of `==`, and reload
under the same name:

```
DLTL -> F x.("(x)mp.has_V(x, 4)")
2,1,66.67,0.0
DLTL -> @cp examples/extra_props.py my_props.py
DLTL -> @sed -i '' "s/== value/>= value/" my_props.py
DLTL -> _LOAD mp my_props.py
DLTL -> F x.("(x)mp.has_V(x, 4)")
3,0,100.0,0.0
```

(`@` runs the rest of the line in the shell; you can of course edit the file
in an editor instead.) Now every trace has an event with `V >= 4`. The
formulas checked before the reload keep their results in `_WRITE`; only the
formulas typed afterwards see the new definition.

### Several files at once

Each `_LOAD` gets its own name, so different files coexist:

```
DLTL -> _LOAD other examples/extra_props.py
DLTL -> F x.("(x)other.has_V(x, 4) and not mp.has_V(x, 5)")
2,1,66.67,0.0
DLTL -> G x.("(x)mp.has_V(x, 1)")
3,0,100.0,0.0
```

`other.has_V` is the original `==` version and `mp.has_V` the edited `>=`
one, so the first formula selects the traces with an event whose `V` is
exactly 4; the second holds because every event has `V >= 1`.

### Loading from an init file

If you always need the same functions, put the `_LOAD` in the init file so
that they are available from the first formula:

```
$ cat props.init
_LOAD mp examples/extra_props.py
$ echo 'F x.("(x)mp.f(x[V]) == 20")' | dltl-mc --log-file examples/sample \
      --init-file props.init --no-interactive
2,1,66.67,0.0
```

### What to keep in mind

- The file is executed as Python code when loaded: only load files you
  trust, exactly as with formulas (which are evaluated with `eval`).
- Errors are reported and the session continues: a missing file, a name
  that is not an identifier, or an exception raised inside the file when it
  is executed.
- `_LOAD` is a session command, not part of the formula language, so it
  cannot be produced by a macro (`_SET`).
- To replace the default `PROP` module for the whole run, use the
  command-line option `--propositions my_props.py` instead.
