# The benchmark formulas

Fifty formulas over the Synthea logs, with the results of checking them on
eight of the logs. They are here **to show what each formula returns**: how
many traces satisfy it and which ones. They are not a measurement of
performance; the times in the result files are those of one run.

`formulas.txt` holds the 50 formulas, each followed by `_WHO`. Nineteen
formulas are purely temporal, eighteen use freeze variables to compare
attributes of the log and thirteen (1 to 10, 43, 48 and 49) call a semantic
proposition of [`propositions.py`](../propositions.py), which receives the
event as `x[Event]` and asks the knowledge graph of that event.

The results are those of five logs with traces of 6 to 20 events, from 50
to 100 000 traces, and of the four ranges of trace length with 10 000
traces:

| Log | Traces | Events | Result files |
| --- | ---: | ---: | --- |
| `log_50_6_20` | 50 | 390 | `results-log_50_6_20.txt` (complete output) |
| `log_5000_6_20` | 5 000 | 38 579 | `results-log_5000_6_20.txt` (complete output) |
| `log_10000_6_20` | 10 000 | 64 705 | `results-log_10000_6_20.txt` (result lines) and `results-log_10000_6_20-full.txt.gz` (complete output) |
| `log_50000_6_20` | 50 000 | 324 003 | `results-log_50000_6_20.txt` (result lines) and `results-log_50000_6_20-full.txt.gz` (complete output) |
| `log_100000_6_20` | 100 000 | 648 926 | `results-log_100000_6_20.txt` (result lines) and `results-log_100000_6_20-full.txt.gz` (complete output) |
| `log_10000_21_40` | 10 000 | 129 993 | `results-log_10000_21_40.txt` (result lines) and `results-log_10000_21_40-full.txt.gz` (complete output) |
| `log_10000_41_60` | 10 000 | 197 081 | `results-log_10000_41_60.txt` (result lines) and `results-log_10000_41_60-full.txt.gz` (complete output) |
| `log_10000_61_80` | 10 000 | 261 972 | `results-log_10000_61_80.txt` (result lines) and `results-log_10000_61_80-full.txt.gz` (complete output) |

## Running them

The propositions need the Oxigraph store of the log that is checked (see
[Setup](../README.md#setup)). For the small log, from the root of the
repository:

```
python examples/synthea/build_store.py examples/synthea/logs/log_50_6_20.nq
dltl-mc --log-file examples/synthea/logs/log_50_6_20 --propositions examples/synthea/propositions.py \
        --formula-file examples/synthea/benchmark/formulas.txt --no-interactive
```

`make synthea-benchmark` does both steps. For any other log, with its own
store (all but the smallest log are gzipped; `--log-file` reads a `.mod.gz`
and `build_store.py` a `.nq.gz`):

```
python examples/synthea/build_store.py examples/synthea/logs/log_5000_6_20.nq.gz store5000
SYNTHEA_STORE=store5000 dltl-mc --log-file examples/synthea/logs/log_5000_6_20 \
        --propositions examples/synthea/propositions.py \
        --formula-file examples/synthea/benchmark/formulas.txt --no-interactive
```

These are the times of the runs whose results are here (Apple M4 Pro, one
run each, some of them while other work was running on the machine):

| Log | Traces | Events | Time of the 50 formulas | Per event |
| --- | ---: | ---: | ---: | ---: |
| `log_50_6_20` | 50 | 390 | 0.5 s | 1.4 ms |
| `log_5000_6_20` | 5 000 | 38 579 | 58.8 s | 1.5 ms |
| `log_10000_6_20` | 10 000 | 64 705 | 98 s (2 min) | 1.5 ms |
| `log_50000_6_20` | 50 000 | 324 003 | 519 s (9 min) | 1.6 ms |
| `log_100000_6_20` | 100 000 | 648 926 | 1020 s (17 min) | 1.6 ms |
| `log_10000_21_40` | 10 000 | 129 993 | 342 s (6 min) | 2.6 ms |
| `log_10000_41_60` | 10 000 | 197 081 | 821 s (14 min) | 4.2 ms |
| `log_10000_61_80` | 10 000 | 261 972 | 1564 s (26 min) | 6.0 ms |

With traces of the same length the time grows with the number of events
(about 1.5 ms per event in the 6-20 range); longer traces cost more per
event, up to 6 ms in the 61-80 range.

## Larger logs

Logs are generated with [`generate_logs.py`](../generate_logs.py) (see
[Generating new logs](../README.md#generating-new-logs)). `--traces` is the
number of traces **per module**, and ten modules are simulated, so the log
has ten times that number of traces: `--traces 5000` gives 50 000 traces and
`--traces 10000` gives 100 000. `--min-steps` and `--max-steps` bound the
length of a trace, and with `--seed` (and `--base-time`, the origin of the
timestamps) the same command always writes the same files. The name of the
log is `log_<traces>_<min>_<max>`, and `--out-dir` writes the files
somewhere other than `examples/synthea/logs`.

The six logs of 10 000 traces or more were generated, in a few seconds
each, with `--seed 42 --base-time 1700000000`; for instance

```
python examples/synthea/generate_logs.py --traces 1000 --min-steps 61 --max-steps 80 \
        --seed 42 --base-time 1700000000
python examples/synthea/generate_logs.py --traces 10000 --min-steps 6 --max-steps 20 \
        --seed 42 --base-time 1700000000
```

write `log_10000_61_80` and `log_100000_6_20`. The repository ships them
gzipped; these are their sizes, and that of the store built from each:

| Log | Events | Quads | `.mod` | `.nq` | `.mod.gz` | `.nq.gz` | Store |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `log_10000_6_20` | 64 705 | 379 745 | 11 MB | 79 MB | 0.5 MB | 3 MB | 65 MB |
| `log_10000_21_40` | 129 993 | 769 226 | 21 MB | 163 MB | 0.9 MB | 7 MB | 130 MB |
| `log_10000_41_60` | 197 081 | 1 165 599 | 32 MB | 249 MB | 1 MB | 10 MB | 194 MB |
| `log_10000_61_80` | 261 972 | 1 547 277 | 43 MB | 332 MB | 2 MB | 12 MB | 253 MB |
| `log_50000_6_20` | 324 003 | 1 899 520 | 54 MB | 397 MB | 2 MB | 13 MB | 317 MB |
| `log_100000_6_20` | 648 926 | 3 807 371 | 108 MB | 797 MB | 4 MB | 27 MB | 619 MB |

A larger log, or another range of trace length, is generated, loaded and
checked in the same way; gzip its files before adding them to a commit.

## Reading the result files

A result file is the output of one of the commands above. After the seven
lines that describe the log there are two lines per formula, in the order of
`formulas.txt`:

1. the result, `yes,no,pct,seconds`: the traces that satisfy the formula,
   those that do not, the percentage of the former and the checking time;
2. the output of `_WHO`: the identifiers of the traces that satisfy the
   formula, separated by spaces (an empty line when none does).

Formula *n* is at lines *2n + 6* and *2n + 7*:

```
$ sed -n '24,25p' examples/synthea/benchmark/results-log_50_6_20.txt | cut -c1-72
50,0,100.0,0.02
allergies_trace_1 allergies_trace_2 allergies_trace_3 allergies_trace_4
$ sed -n '8p' examples/synthea/benchmark/results-log_5000_6_20.txt
4992,8,99.84,1.15
```

From 10 000 traces on, the `_WHO` lists make files of 8 to 82 MB, too large
to be displayed on GitHub. For those logs `results-<log>.txt` holds the
result lines only, one per formula (formula *n* is at line *n + 7*), and the
complete output, with the layout described above, is in
`results-<log>-full.txt.gz`:

```
$ gunzip -c examples/synthea/benchmark/results-log_50000_6_20-full.txt.gz | sed -n '8,9p' | cut -c1-72
49939,61,99.88,11.13
allergies_trace_1 allergies_trace_10 allergies_trace_100 allergies_trace
```

A file with the result lines is the complete output without the `_WHO`
lines. To produce only the result lines, leave `_WHO` out of the run:

```
grep -v '^_WHO' examples/synthea/benchmark/formulas.txt | SYNTHEA_STORE=store50000 dltl-mc \
        --log-file examples/synthea/logs/log_50000_6_20 \
        --propositions examples/synthea/propositions.py --no-interactive
```

## Results

Traces that satisfy each formula in the logs with traces of 6 to 20 events,
out of 50, 5000, 10 000, 50 000 and 100 000:

| # | Formula | `log_50_6_20` | `log_5000_6_20` | `log_10000_6_20` | `log_50000_6_20` | `log_100000_6_20` |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `G (x.("(x)PROP.Asthma(x[Event])") -> at_AllergyOnset)` | 50 | 4992 | 9990 | 49939 | 99890 |
| 2 | `G ((breast_cancer & at_MedicationOrder) -> x.("(x)PROP.Inhaled_steroid_therapy(x[Event])"))` | 50 | 5000 | 10000 | 50000 | 100000 |
| 3 | `G ((Allergy_Panel & SCTID_252325008) -> (Practitioner & x.("(x)PROP.Gynecology_service(x[Event])")))` | 50 | 5000 | 10000 | 50000 | 100000 |
| 4 | `G (Potential_COPD_Smoker -> X x.("(x)PROP.Smoking_cessation_therapy(x[Event])"))` | 45 | 4500 | 9000 | 45000 | 90000 |
| 5 | `G (at_AllergyOnset -> x.("(x)PROP.Atopic_dermatitis(x[Event])"))` | 45 | 4536 | 9067 | 45314 | 90682 |
| 6 | `G (Drug_Allergy_Incidence_Submodule -> (at_MedicationOrder -> x.("(x)PROP.Administration_of_intravenous_fluids(x[Event])")))` | 50 | 5000 | 10000 | 50000 | 100000 |
| 7 | `G (Allergist_Guard -> (!(x.("(x)PROP.Malignant_neoplasm_of_breast(x[Event])"))))` | 50 | 5000 | 10000 | 50000 | 100000 |
| 8 | `G (Prescribe_Epipen -> x.("(x)PROP.Allergic_disposition(x[Event])"))` | 48 | 4863 | 9712 | 48608 | 97179 |
| 9 | `G (Administer_Allergy_Test -> F (x.("(x)PROP.Asthma_screening(x[Event])") \| x.("(x)PROP.Allergy_screening_test(x[Event])")))` | 50 | 5000 | 10000 | 50000 | 100000 |
| 10 | `G (Allergy_Unspecified -> x.("(x)PROP.Contact_dermatitis(x[Event])"))` | 45 | 4536 | 9067 | 45314 | 90682 |
| 11 | `G (Administer_Allergy_Test & x.(X (Allergy_Panel & y.("(x,y)x[Actor] == y[Actor]"))))` | 0 | 0 | 0 | 0 | 0 |
| 12 | `G (Allergist_Initial_Visit & x.(F (End_Allergist_Initial_Visit & y.("(x,y)y[Timestamp] - x[Timestamp] < 3600"))))` | 0 | 0 | 0 | 0 | 0 |
| 13 | `G (Drug_Allergy_Incidence_Submodule & x.(F (General_Allergy_CarePlan & y.("(x,y)y[#] == x[#] + 3"))))` | 0 | 0 | 0 | 0 | 0 |
| 14 | `G (Initial & x.(G (at_Procedure -> y.("(x,y)x[Timestamp] < y[Timestamp]"))))` | 0 | 0 | 2236 | 11183 | 22293 |
| 15 | `G (Physician & Allergist_Initial_Visit & x.(G (at_MedicationOrder -> y.("(x,y)x[Actor] == y[Actor]"))))` | 0 | 0 | 0 | 0 | 0 |
| 16 | `G (Environmental_Allergy_Incidence_Submodule & x.(F (Food_Allergy_Incidence_Submodule & y.("(x,y)x[Timestamp] < y[Timestamp]"))))` | 0 | 0 | 0 | 0 | 0 |
| 17 | `G (Practitioner & at_Encounter & x.(F (at_Terminal & y.("(x,y)x[Actor] != y[Actor]"))))` | 0 | 0 | 0 | 0 | 0 |
| 18 | `G (Atopic & x.(F (Prescribe_OTC_Antihistamine & y.("(x,y)y[#] <= x[#] + 10"))))` | 0 | 0 | 0 | 0 | 0 |
| 19 | `G (Clinical_System & at_Guard & x.(X (at_Delay & y.("(x,y)x[Actor] == y[Actor]"))))` | 0 | 0 | 0 | 0 | 0 |
| 20 | `G (Immunotherapy_Submodule & y.(O (Allergy_Panel & x.("(x,y)x[#] < y[#]"))))` | 0 | 0 | 0 | 0 | 0 |
| 21 | `G (at_AllergyOnset -> x.(F (Atopic & y.("(x,y)y[Timestamp] - x[Timestamp] <= 7200"))))` | 45 | 4536 | 9067 | 45314 | 90682 |
| 22 | `G (Allergist_Initial_Visit -> (at_Encounter U at_EncounterEnd))` | 46 | 4617 | 9201 | 46013 | 92066 |
| 23 | `G (Prescribe_Epipen -> (Administer_Allergy_Test S Initial))` | 48 | 4863 | 9712 | 48608 | 97179 |
| 24 | `G (Delay_For_Atopy -> ! X Not_Atopic)` | 43 | 4522 | 9005 | 44957 | 89940 |
| 25 | `G (Living_With_Allergies -> (Living_With_Allergies U Terminal))` | 48 | 4798 | 9527 | 47693 | 95410 |
| 26 | `G (Delay_For_Allergist_Initial_Visit -> x.(F (Allergist_Initial_Visit & y.("(x,y)y[Timestamp] - x[Timestamp] >= 86400"))))` | 46 | 4580 | 9137 | 45668 | 91365 |
| 27 | `Initial & (Y !true)` | 0 | 0 | 0 | 0 | 0 |
| 28 | `G ((at_CallSubmodule & Immunotherapy_Submodule) -> x.(O (Allergy_Panel & y.("(x,y)x[Timestamp] - y[Timestamp] == 2592000"))))` | 48 | 4798 | 9594 | 48044 | 96064 |
| 29 | `G (Potential_COPD_Nonsmoker -> ! O Potential_COPD_Smoker)` | 50 | 5000 | 10000 | 50000 | 100000 |
| 30 | `G (at_Simple -> (x.(F (at_Simple & y.("(x,y)y[Timestamp] - x[Timestamp] <= 14400")) \| F Terminal)))` | 50 | 5000 | 10000 | 50000 | 100000 |
| 31 | `G ((allergies & !Allergist_Guard) -> X General_Allergy_CarePlan)` | 45 | 4500 | 9000 | 45000 | 90000 |
| 32 | `G (at_MedicationOrder -> Pharmacist)` | 48 | 4843 | 9677 | 48428 | 96819 |
| 33 | `G (Allergy_Unspecified -> !Radiologist)` | 50 | 5000 | 10000 | 50000 | 100000 |
| 34 | `F (Clinical_System & Age_Guard & X at_Guard)` | 0 | 0 | 0 | 0 | 0 |
| 35 | `G (copd -> ((Potential_COPD_Smoker \| Potential_COPD_Nonsmoker) U Terminal))` | 45 | 4500 | 9000 | 45000 | 90000 |
| 36 | `G ((at_CallSubmodule & Drug_Allergy_Incidence_Submodule) -> !(X at_CarePlanStart \| X X at_CarePlanStart \| X X X at_CarePlanStart))` | 50 | 5000 | 10000 | 50000 | 100000 |
| 37 | `G ((Allergist_Initial_Visit & at_Initial) -> x.(F (End_Allergist_Initial_Visit & y.("(x,y)x[Actor] == y[Actor] and x[Actor] == 'Physician'"))))` | 50 | 5000 | 10000 | 50000 | 100000 |
| 38 | `G (fibromyalgia -> (Initial -> X (at_Simple & X (at_Simple & X at_Simple))))` | 45 | 4500 | 9000 | 45000 | 90000 |
| 39 | `G (Care_Manager -> (General_Allergy_CarePlan \| Delay_For_Atopy))` | 50 | 5000 | 10000 | 50000 | 100000 |
| 40 | `G (at_Procedure -> x.("(x)x[Actor] == 'Practitioner' and x[Actor] != 'Clinical_System'"))` | 42 | 4368 | 8709 | 43478 | 86931 |
| 41 | `G (x.("(x)x[#] > 100") -> (F Terminal & !X X X X X X Terminal))` | 50 | 5000 | 10000 | 50000 | 100000 |
| 42 | `G (at_Delay & x.("(x)x[Timestamp] < 0") -> X Terminal)` | 50 | 5000 | 10000 | 50000 | 100000 |
| 43 | `G (x.("(x)PROP.Chronic_obstructive_bronchitis(x[Event])") -> (O Potential_COPD_Smoker & y.("(y)y[Actor] == 'Physician'")))` | 50 | 5000 | 10000 | 50000 | 100000 |
| 44 | `G ((Administer_Allergy_Test & at_Procedure) -> X (Allergy_Panel & at_CallSubmodule))` | 50 | 4980 | 9964 | 49822 | 99659 |
| 45 | `G (at_Encounter -> (!at_Terminal U at_EncounterEnd))` | 44 | 4441 | 9069 | 45375 | 90811 |
| 46 | `G ((Allergist_Guard & at_Guard) -> X (!at_Terminal & (!at_Terminal U at_Procedure)))` | 48 | 4661 | 9344 | 46836 | 93655 |
| 47 | `G (Initial -> X (Terminal \| F !Terminal))` | 50 | 5000 | 7764 | 38817 | 77707 |
| 48 | `G (x.("(x)PROP.Malignant_neoplasm_of_colon(x[Event])") -> F (Colonoscopy & F General_Allergy_CarePlan))` | 50 | 5000 | 9998 | 49998 | 99988 |
| 49 | `G ((breast_cancer & at_Initial) -> X (!(x.("(x)PROP.Surgical_procedure(x[Event])" \| "(x)PROP.Therapeutic_procedure(x[Event])")) U Female))` | 48 | 4752 | 9514 | 47487 | 94995 |
| 50 | `G (dermatitis -> !Prescribe_Epipen)` | 50 | 5000 | 10000 | 50000 | 100000 |

Traces that satisfy each formula in the logs of 10 000 traces, by range of
trace length:

| # | Formula | `log_10000_6_20` | `log_10000_21_40` | `log_10000_41_60` | `log_10000_61_80` |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `G (x.("(x)PROP.Asthma(x[Event])") -> at_AllergyOnset)` | 9990 | 9851 | 9766 | 9782 |
| 2 | `G ((breast_cancer & at_MedicationOrder) -> x.("(x)PROP.Inhaled_steroid_therapy(x[Event])"))` | 10000 | 9984 | 9968 | 9960 |
| 3 | `G ((Allergy_Panel & SCTID_252325008) -> (Practitioner & x.("(x)PROP.Gynecology_service(x[Event])")))` | 10000 | 10000 | 10000 | 10000 |
| 4 | `G (Potential_COPD_Smoker -> X x.("(x)PROP.Smoking_cessation_therapy(x[Event])"))` | 9000 | 9000 | 9000 | 9000 |
| 5 | `G (at_AllergyOnset -> x.("(x)PROP.Atopic_dermatitis(x[Event])"))` | 9067 | 9000 | 9000 | 9000 |
| 6 | `G (Drug_Allergy_Incidence_Submodule -> (at_MedicationOrder -> x.("(x)PROP.Administration_of_intravenous_fluids(x[Event])")))` | 10000 | 10000 | 10000 | 10000 |
| 7 | `G (Allergist_Guard -> (!(x.("(x)PROP.Malignant_neoplasm_of_breast(x[Event])"))))` | 10000 | 10000 | 10000 | 10000 |
| 8 | `G (Prescribe_Epipen -> x.("(x)PROP.Allergic_disposition(x[Event])"))` | 9712 | 9518 | 9518 | 9518 |
| 9 | `G (Administer_Allergy_Test -> F (x.("(x)PROP.Asthma_screening(x[Event])") \| x.("(x)PROP.Allergy_screening_test(x[Event])")))` | 10000 | 10000 | 10000 | 10000 |
| 10 | `G (Allergy_Unspecified -> x.("(x)PROP.Contact_dermatitis(x[Event])"))` | 9067 | 9000 | 9000 | 9000 |
| 11 | `G (Administer_Allergy_Test & x.(X (Allergy_Panel & y.("(x,y)x[Actor] == y[Actor]"))))` | 0 | 0 | 0 | 0 |
| 12 | `G (Allergist_Initial_Visit & x.(F (End_Allergist_Initial_Visit & y.("(x,y)y[Timestamp] - x[Timestamp] < 3600"))))` | 0 | 0 | 0 | 0 |
| 13 | `G (Drug_Allergy_Incidence_Submodule & x.(F (General_Allergy_CarePlan & y.("(x,y)y[#] == x[#] + 3"))))` | 0 | 0 | 0 | 0 |
| 14 | `G (Initial & x.(G (at_Procedure -> y.("(x,y)x[Timestamp] < y[Timestamp]"))))` | 2236 | 2232 | 2231 | 2224 |
| 15 | `G (Physician & Allergist_Initial_Visit & x.(G (at_MedicationOrder -> y.("(x,y)x[Actor] == y[Actor]"))))` | 0 | 0 | 0 | 0 |
| 16 | `G (Environmental_Allergy_Incidence_Submodule & x.(F (Food_Allergy_Incidence_Submodule & y.("(x,y)x[Timestamp] < y[Timestamp]"))))` | 0 | 0 | 0 | 0 |
| 17 | `G (Practitioner & at_Encounter & x.(F (at_Terminal & y.("(x,y)x[Actor] != y[Actor]"))))` | 0 | 0 | 0 | 0 |
| 18 | `G (Atopic & x.(F (Prescribe_OTC_Antihistamine & y.("(x,y)y[#] <= x[#] + 10"))))` | 0 | 0 | 0 | 0 |
| 19 | `G (Clinical_System & at_Guard & x.(X (at_Delay & y.("(x,y)x[Actor] == y[Actor]"))))` | 0 | 0 | 0 | 0 |
| 20 | `G (Immunotherapy_Submodule & y.(O (Allergy_Panel & x.("(x,y)x[#] < y[#]"))))` | 0 | 0 | 0 | 0 |
| 21 | `G (at_AllergyOnset -> x.(F (Atopic & y.("(x,y)y[Timestamp] - x[Timestamp] <= 7200"))))` | 9067 | 9000 | 9000 | 9000 |
| 22 | `G (Allergist_Initial_Visit -> (at_Encounter U at_EncounterEnd))` | 9201 | 9000 | 9000 | 9000 |
| 23 | `G (Prescribe_Epipen -> (Administer_Allergy_Test S Initial))` | 9712 | 9518 | 9518 | 9518 |
| 24 | `G (Delay_For_Atopy -> ! X Not_Atopic)` | 9005 | 8999 | 8994 | 8993 |
| 25 | `G (Living_With_Allergies -> (Living_With_Allergies U Terminal))` | 9527 | 9000 | 9000 | 9000 |
| 26 | `G (Delay_For_Allergist_Initial_Visit -> x.(F (Allergist_Initial_Visit & y.("(x,y)y[Timestamp] - x[Timestamp] >= 86400"))))` | 9137 | 9000 | 9000 | 9000 |
| 27 | `Initial & (Y !true)` | 0 | 0 | 0 | 0 |
| 28 | `G ((at_CallSubmodule & Immunotherapy_Submodule) -> x.(O (Allergy_Panel & y.("(x,y)x[Timestamp] - y[Timestamp] == 2592000"))))` | 9594 | 9000 | 9000 | 9000 |
| 29 | `G (Potential_COPD_Nonsmoker -> ! O Potential_COPD_Smoker)` | 10000 | 10000 | 10000 | 10000 |
| 30 | `G (at_Simple -> (x.(F (at_Simple & y.("(x,y)y[Timestamp] - x[Timestamp] <= 14400")) \| F Terminal)))` | 10000 | 10000 | 10000 | 10000 |
| 31 | `G ((allergies & !Allergist_Guard) -> X General_Allergy_CarePlan)` | 9000 | 9000 | 9000 | 9000 |
| 32 | `G (at_MedicationOrder -> Pharmacist)` | 9677 | 9394 | 9224 | 9120 |
| 33 | `G (Allergy_Unspecified -> !Radiologist)` | 10000 | 10000 | 10000 | 10000 |
| 34 | `F (Clinical_System & Age_Guard & X at_Guard)` | 0 | 0 | 0 | 0 |
| 35 | `G (copd -> ((Potential_COPD_Smoker \| Potential_COPD_Nonsmoker) U Terminal))` | 9000 | 9000 | 9000 | 9000 |
| 36 | `G ((at_CallSubmodule & Drug_Allergy_Incidence_Submodule) -> !(X at_CarePlanStart \| X X at_CarePlanStart \| X X X at_CarePlanStart))` | 10000 | 10000 | 10000 | 10000 |
| 37 | `G ((Allergist_Initial_Visit & at_Initial) -> x.(F (End_Allergist_Initial_Visit & y.("(x,y)x[Actor] == y[Actor] and x[Actor] == 'Physician'"))))` | 10000 | 10000 | 10000 | 10000 |
| 38 | `G (fibromyalgia -> (Initial -> X (at_Simple & X (at_Simple & X at_Simple))))` | 9000 | 9000 | 9000 | 9000 |
| 39 | `G (Care_Manager -> (General_Allergy_CarePlan \| Delay_For_Atopy))` | 10000 | 10000 | 10000 | 10000 |
| 40 | `G (at_Procedure -> x.("(x)x[Actor] == 'Practitioner' and x[Actor] != 'Clinical_System'"))` | 8709 | 8155 | 7931 | 7857 |
| 41 | `G (x.("(x)x[#] > 100") -> (F Terminal & !X X X X X X Terminal))` | 10000 | 10000 | 10000 | 10000 |
| 42 | `G (at_Delay & x.("(x)x[Timestamp] < 0") -> X Terminal)` | 10000 | 10000 | 10000 | 10000 |
| 43 | `G (x.("(x)PROP.Chronic_obstructive_bronchitis(x[Event])") -> (O Potential_COPD_Smoker & y.("(y)y[Actor] == 'Physician'")))` | 10000 | 10000 | 10000 | 10000 |
| 44 | `G ((Administer_Allergy_Test & at_Procedure) -> X (Allergy_Panel & at_CallSubmodule))` | 9964 | 10000 | 10000 | 10000 |
| 45 | `G (at_Encounter -> (!at_Terminal U at_EncounterEnd))` | 9069 | 9599 | 9532 | 9526 |
| 46 | `G ((Allergist_Guard & at_Guard) -> X (!at_Terminal & (!at_Terminal U at_Procedure)))` | 9344 | 9505 | 9505 | 9505 |
| 47 | `G (Initial -> X (Terminal \| F !Terminal))` | 7764 | 7768 | 7769 | 7776 |
| 48 | `G (x.("(x)PROP.Malignant_neoplasm_of_colon(x[Event])") -> F (Colonoscopy & F General_Allergy_CarePlan))` | 9998 | 9990 | 9989 | 9988 |
| 49 | `G ((breast_cancer & at_Initial) -> X (!(x.("(x)PROP.Surgical_procedure(x[Event])" \| "(x)PROP.Therapeutic_procedure(x[Event])")) U Female))` | 9514 | 9488 | 9495 | 9503 |
| 50 | `G (dermatitis -> !Prescribe_Epipen)` | 10000 | 10000 | 10000 | 10000 |

## Notes

- The formulas are kept as they were checked for the benchmark. Eight of them
  (3, 15, 17, 19, 32, 33, 34 and 39) use the name of an actor
  (`Practitioner`, `Physician`, `Clinical_System`, `Pharmacist`, `Radiologist`,
  `Care_Manager`) as an atomic proposition. In these logs the actor is the
  string attribute `Actor`, not an atomic proposition, so such a name holds
  at no event: `G (at_MedicationOrder -> Pharmacist)` is satisfied by the
  traces without a medication order. The condition on the actor is written
  as a data expression, as formulas 37, 40 and 43 do:
  `G (at_MedicationOrder -> x.("(x)x[Actor] == 'Pharmacist'"))`.
- For the same reason `SCTID_252325008` (formula 3) and `Colonoscopy`
  (formula 48) hold at no event: neither is an atomic proposition of these
  logs.
