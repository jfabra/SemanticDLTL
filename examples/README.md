# Examples

| File | Content |
| --- | --- |
| `sample.mod` | Tiny model with three traces and one attribute of each type (used by the tests) |
| `sample.init` | Init file defining two macros with `_SET` |
| `formulas.txt` | Formulas exercising the freeze operator, data expressions, macros, `_WRITE` and `_BYE` |
| `sample2.mod` | Four traces with an extra string attribute `Extra` |
| `formulas2.txt` | Two formulas on `sample2` combining nested freezes with `U` and `H` |
| `extra_props.py` | Propositions to load during a session with `_LOAD` |
| `session_macros.txt` | A session showing `_SET`, `_RE` and `_RANGE` macros |
| `semantic/` | Larger, ontology-annotated event logs (see its README) |

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
DLTL -> _LOAD mp examples/extra_props.py
DLTL -> F x.("(x)mp.f(x[V]) == 8")
2,1,66.67,0.0
DLTL -> _BYE
```
