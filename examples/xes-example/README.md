# An XES event log: the Conformance Checking Challenge 2019

This example checks DLTL formulas directly on an event log in
[XES](https://www.xes-standard.org/) format, without any intermediate `.mod`
file. The log is the one of the Conformance Checking Challenge 2019 (CCC19):
recordings of medical students installing a central venous catheter (CVC)
guided by ultrasound, a procedure in which a catheter is placed in a central
vein to deliver fluids or medication.

| File | Content |
| --- | --- |
| `xes-example.xes` | the event log: 20 traces, 1394 events |
| `xes-example.schema.xml` | mapping schema: the type and the name that each XES attribute gets in the model |
| `formulas.txt` | the formulas of the session below, ready for a batch run |

## The data

Each trace is one recorded procedure, of 52 to 118 events. Every activity
contributes two events, a `start` and a `complete`, so the 1394 events are
697 executions of 29 activities. This is one event of the log:

```xml
<trace>
    <string key="concept:name" value="1539302414925-video_1.3_CVC"/>
    ...
    <event>
        <string key="concept:name" value="Hand washing"/>
        <string key="lifecycle:transition" value="start"/>
        <string key="org:resource" value="R_13_1C"/>
        <date key="time:timestamp" value="2018-10-11T23:00:00.000+11:00"/>
        <string key="RESOURCE" value="R_13_1C"/>
        <string key="ROUND" value="Pre"/>
        <string key="EVENTID" value="1539301115461"/>
        <string key="ACTIVITY" value="Hand washing"/>
        <string key="STAGE" value="Operator and Patient Preparation"/>
        <string key="VIDEOSTART" value="55"/>
        <string key="VIDEOEND" value="67"/>
    </event>
```

| XES attribute | Meaning |
| --- | --- |
| `concept:name`, `ACTIVITY` | name of the activity (`Hand washing`, `Puncture`, `Guidewire install`, ...) |
| `lifecycle:transition` | `start` or `complete` |
| `org:resource`, `RESOURCE` | who performs the procedure: one resource per trace, and each of the ten resources has one procedure in each round |
| `time:timestamp` | date and time of the event |
| `ROUND` | `Pre` or `Post`: the round the procedure belongs to, ten procedures each |
| `EVENTID` | identifier of the execution of the activity, shared by its `start` and `complete` events |
| `STAGE` | stage of the procedure the activity belongs to (see below) |
| `VIDEOSTART`, `VIDEOEND` | where the activity starts and ends in the video recording |

The activities are grouped in six stages:

| `STAGE` | Activities |
| --- | --- |
| `Operator and Patient Preparation` | Hand washing, Get in sterile clothes, Clean puncture area, Drap puncture area, Prepare implements |
| `Ultrasound Preparation` | Ultrasound configuration, Gel in probe, Cover probe, Put sterile gel, Position probe |
| `Locate Structures` | Position patient, Anatomic identification, Compression identification, Doppler identification |
| `Venous puncture` | Anesthetize, Puncture, Blood return |
| `Install Guidewire` | Remove syringe, Guidewire install, Remove trocar, Drop probe, Check wire in short axis, Check wire in long axis, Wire in good position |
| `Install Catheter` | Widen pathway, Advance catheter, Remove guidewire, Check flow and reflow, Check catheter position |

## Reading the log without a schema

The checker reads the `.xes` file as it is:

```
$ dltl-mc --log-file examples/xes-example/xes-example.xes
----------------------------------------
file:      examples/xes-example/xes-example.xes
#traces:   20
#events:   1394
#atomics:  29
att. desc: ['aconcept:name', 'slifecycle:transition', 'sorg:resource', 'ntime:timestamp', 'sRESOURCE', 'sROUND', 'sEVENTID', 'sACTIVITY', 'sSTAGE', 'sVIDEOSTART', 'sVIDEOEND']
----------------------------------------
DLTL -> F Doppler_identification
5,15,25.0,0.0
```

By default the activity (`concept:name`) is an atomic proposition, written
as an identifier (`Doppler identification` is `Doppler_identification`), and
every other attribute keeps its XES name and the type that its XES type
suggests: strings stay strings and the date becomes a number. That is enough
to ask about activities, but it falls short here in three ways:

* `lifecycle:transition` is a string, so "a start event" has to be written
  as a data expression, and with `COL[...]` because the name is not a Python
  identifier: `x.("(x)x[COL['lifecycle:transition']] == 'start'")`;
* `VIDEOSTART` and `VIDEOEND` are strings in the XES file, so they compare
  as text: `'137' >= '84'` is false;
* names such as `time:timestamp` are awkward to write.

```
DLTL -> G x.("(x)x[VIDEOEND] >= x[VIDEOSTART]")
3,17,15.0,0.01
```

Only three procedures seem to have every activity ending after it starts,
which is an artefact of comparing strings.

## The mapping schema

`xes-example.schema.xml` gives each attribute the type and the name that suit
the formulas. The first character of `value` is the type (`a` atomic
proposition, `s` string, `n` number), the rest is the name:

```xml
<container key="mod:schema">
    <string key="concept:name" value="aactivity"/>
    <string key="lifecycle:transition" value="atransition"/>
    <string key="org:resource" value="aresource"/>
    <string key="time:timestamp" value="ntimestamp"/>
    <string key="RESOURCE" value="aRESOURCE"/>
    <string key="ROUND" value="sROUND"/>
    <string key="EVENTID" value="aEVENTID"/>
    <string key="ACTIVITY" value="sACTIVITY"/>
    <string key="STAGE" value="sSTAGE"/>
    <string key="VIDEOSTART" value="nVIDEOSTART"/>
    <string key="VIDEOEND" value="nVIDEOEND"/>
</container>
```

With it:

* the activity, the transition, the resource and the event identifier are
  **atomic propositions**: `Puncture`, `start`, `complete`, `R_13_1C` and
  `_1539301115461` can be written directly in formulas (an identifier cannot
  start with a digit, hence the `_`);
* `timestamp`, `VIDEOSTART` and `VIDEOEND` are **numbers**; the timestamp is
  the number of milliseconds since 1970-01-01 00:00:00 UTC;
* `ROUND`, `ACTIVITY` and `STAGE` are **strings**, kept as they are
  (`'Install Catheter'`, with its space), for data expressions.

The trace identifier is the `concept:name` of the trace, also as an
identifier: `1539302414925-video_1.3_CVC` is trace
`_1539302414925_video_1_3_CVC`.

## A session, step by step

```
$ dltl-mc --log-file examples/xes-example/xes-example.xes \
          --xes-schema examples/xes-example/xes-example.schema.xml
----------------------------------------
file:      examples/xes-example/xes-example.xes
#traces:   20
#events:   1394
#atomics:  738
att. desc: ['aactivity', 'atransition', 'aresource', 'ntimestamp', 'aRESOURCE', 'sROUND', 'aEVENTID', 'sACTIVITY', 'sSTAGE', 'nVIDEOSTART', 'nVIDEOEND']
----------------------------------------
```

**Activities and their order.** Which procedures use Doppler to identify
the vessels, and is every puncture preceded by the anaesthesia?

```
DLTL -> F Doppler_identification
5,15,25.0,0.0
DLTL -> G (Puncture -> O Anesthetize)
18,2,90.0,0.0
DLTL -> _WHO_NOT
_1539739275781_video_4_5_CVC _1539832275246_video_4_8_CVC
```

Five of the twenty; and in two procedures there is a puncture with no
anaesthesia before it. Since the transitions are atomic propositions too, a
repeated puncture is two `start` events of `Puncture`:

```
DLTL -> F (Puncture & start & X F (Puncture & start))
6,14,30.0,0.01
```

**Attributes of one event.** With numeric video positions the comparison
that failed above is the intended one, and it holds in every procedure.
String attributes are compared with their original text: once the
installation of the catheter begins, do the earlier stages ever come back?

```
DLTL -> G x.("(x)x[VIDEOEND] >= x[VIDEOSTART]")
20,0,100.0,0.01
DLTL -> G x.("(x)x[STAGE] == 'Install Catheter'" -> G y.("(y)y[STAGE] == 'Install Catheter'"))
15,5,75.0,0.02
```

In five procedures an activity of an earlier stage is performed after the
installation of the catheter has begun.

**Relating two events.** Do activities overlap? They do not if every
`start` is immediately followed by the `complete` of the same activity:

```
DLTL -> G x.(start -> X y.(complete & "(x,y)x[ACTIVITY] == y[ACTIVITY]"))
9,11,45.0,0.02
```

In eleven procedures some `start` is not directly followed by its own
`complete`: an activity starts while another is in progress.
Timestamps are milliseconds, so durations are differences: a puncture that
takes two minutes or more, and a procedure of more than an hour between its
first event and its last one (`X false` holds only at the last event):

```
DLTL -> F x.(Puncture & start & X y.(Puncture & complete & "(x,y)y[timestamp] - x[timestamp] >= 120000"))
4,16,20.0,0.02
DLTL -> x.(F y.(X false & "(x,y)y[timestamp] - x[timestamp] > 3600000"))
5,15,25.0,0.52
```

**The two rounds.** A macro checks a formula once per round. `ROUND` has
the same value in every event of a trace, so it is read at the first one:

```
DLTL -> _SET ?round 'Pre', 'Post'
DLTL -> x.("(x)x[ROUND] == ?round") & F (Puncture & start & X F (Puncture & start))
5,15,25.0,0.02
1,19,5.0,0.02
DLTL -> x.("(x)x[ROUND] == ?round") & F Check_catheter_position
7,13,35.0,0.01
10,10,50.0,0.01
DLTL -> _BYE
```

The puncture is repeated in five of the ten `Pre` procedures and in one of
the ten `Post` ones, and the position of the catheter is checked in seven
`Pre` procedures and in all ten `Post` ones.

## Batch run

The same formulas are in `formulas.txt`, with comments:

```
dltl-mc --log-file examples/xes-example/xes-example.xes \
        --xes-schema examples/xes-example/xes-example.schema.xml \
        --formula-file examples/xes-example/formulas.txt --no-interactive
```

`make xes-example` runs it. The test-suite runs this file too and compares
the results with `tests/golden/xes-example.stdout`. Adding `_WRITE` to the
session saves the results next to the log, as `xes-example.res`, `.norm` and
`.forms`.

## Other options

* `--xes-ignore` loads only the attributes that appear in the schema; without
  it every attribute is loaded, those missing from the schema with their XES
  name and a default type. This schema names all eleven attributes, so here
  it changes nothing; with a schema of two entries the model would have two
  attributes with `--xes-ignore` and eleven without it.
* `--xes-trace-id-key KEY` takes the trace identifier from another attribute
  of the trace (`variant`, for instance) instead of `concept:name`. Traces
  with the same identifier are loaded as a single trace.
* A gzipped log (`xes-example.xes.gz`) is read in the same way.

The rules that values follow and the default types are in the
[XES event logs](../../README.md#xes-event-logs) section of the main README.

## Source of the data

`xes-example.xes` is the XES log of

> J. Munoz-Gama, R. de la Fuente, M. Sepúlveda, R. Fuentes.
> *Conformance Checking Challenge 2019 (CCC19)*. 4TU.Centre for Research
> Data, 2019. Dataset.
> [doi:10.4121/uuid:c923af09-ce93-44c3-ace0-c5508cf103ad](https://doi.org/10.4121/uuid:c923af09-ce93-44c3-ace0-c5508cf103ad)

distributed under the [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)
license; here it has been renamed.
