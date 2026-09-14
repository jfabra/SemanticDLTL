# DLTL formula grammar

## Operator precedence

From the loosest to the tightest binding. Binary operators are
left-associative; a unary operator applies to the longest formula whose
operators bind at least as tightly.

| Level | Operators | Meaning |
| --- | --- | --- |
| 0 | `->`, `<->` | implication, equivalence |
| 1 | `\|` | or |
| 2 | `&` | and |
| 3 | `U`, `S` | until, since |
| 4 | `F`, `O`, `Fn`, `On` | eventually, once (and their bounded versions) |
| 5 | `G`, `H` | globally, historically |
| 6 | `X`, `Y`, `Xn`, `Yn` | next, previous (and their repeated versions) |
| 7 | `!` | not |

Examples:

| Written | Read as |
| --- | --- |
| `a \| b & c` | `a \| (b & c)` |
| `a -> b & c` | `a -> (b & c)` |
| `F a U b` | `(F a) U b` |
| `!X a` | `!(X a)` |
| `a & b & c` | `(a & b) & c` |

Note: the original prototype parsed `a | b & c` as `(a | b) & c`. This was
changed in version 1.0.0 (see `CHANGELOG.md`).

## Grammar

```
formula  ::= implic
implic   ::= disj (('->' | '<->') disj)*
disj     ::= conj ('|' conj)*
conj     ::= until ('&' until)*
until    ::= unary (('U' | 'S') unary)*
unary    ::= ('!' | 'X' | 'Y' | 'G' | 'H' | 'F' | 'O') unary
           | ('X' | 'Y' | 'F' | 'O') digits unary      -- X3 f, F2 f, ...
           | primary
primary  ::= 'true' | 'false'
           | id                                       -- atomic proposition
           | var '.' '(' formula ')'                  -- freeze operator
           | '"' '(' [var (',' var)*] ')' python-expression '"'
           | '(' formula ')'

id       ::= [a-zA-Z_][a-zA-Z_0-9]*
var      ::= [a-z]
digits   ::= [1-9]+
```

`$` and whitespace are ignored by the lexer (`$` terminates a formula in
multi-line mode). Identifiers `U`, `S`, `X`, `Y`, `G`, `H`, `F`, `O` (and
`X1`, `F2`, ...) are reserved for the operators, so they cannot name atomic
propositions.

## Data expressions

A data expression `"(x,y)<python expression>"` lists the freeze variables it
depends on and gives a Python boolean expression over the events bound to
them:

* `x[<attr>]` is the value of non-atomic attribute `<attr>` in the event
  frozen in `x` (`x[V]`, `x[p]['b']`, `'z' in x[att]`, ...);
* `x[#]` is the position of that event in the trace, starting at 1;
* `COL['<attr>']` is the position of `<attr>` inside the event tuple;
* `PROP.<name>(...)` calls a user-defined proposition (see `--propositions`).

The expression is evaluated when all its variables have been bound; the
variables are bound by name (a variable may appear inside string literals),
so a freeze variable must not be called like an attribute or like `COL`,
`PROP` or `I_POS`.
