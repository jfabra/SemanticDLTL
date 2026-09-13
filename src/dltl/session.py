# -----------------------------------------------------------------------------
# SemanticDLTL: a DLTL model checker over finite traces
#
# Copyright (C) 2024-2026
#   Joaquín Ezpeleta, Universidad de Zaragoza, Spain
#   Javier Fabra, Universidad de Zaragoza, Spain
#   María José Ibáñez, Universidad de La Rioja, Spain
# Contact: semanticdltl@unizar.es
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of SemanticDLTL. It is free software: you can redistribute
# it and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version. See the LICENSE file for details.
#
# Based on: J. M. Couvreur, J. Ezpeleta, "A Linear Temporal Logic Model
# Checking Method over Finite Words with Correlated Transition Attributes",
# SIMPDA 2017, LNBIP vol. 340, Springer, 2019.
# -----------------------------------------------------------------------------
"""
A checking session: a loaded model, the macros defined so far, the accumulated
results of the checked formulas and the commands that operate on them.

Lines given to :meth:`Session.execute` are either commands (starting with
``_``), system calls (starting with ``@``), comments (starting with ``;``) or
DLTL formulas::

    _INFO                       show information about the loaded model
    _SET ?name v1,v2,...        define a macro with the given values
    _RE ?name <regex>           define a macro with the atomics matching the regex
    _RANGE ?name from,to[,step] define a macro with a range of integers
    _LOAD name file.py          load a Python file, usable in formulas as name.<func>
    _WHO / _WHO_NOT             ids of the traces (not) satisfying the last formula
    _WRITE                      save the results to <log>.res, <log>.norm, <log>.forms
    _WRITE_LENGTHS              save the trace lengths to <log>_trace_lengths.csv
    _CLEAR_DATA                 forget the checked formulas and their results
    _AGUR / _BYE                end the session (also ``agur``)
    @<command>                  run <command> in the operating system shell

Macros are expanded only in formulas: a macro whose value is a command name
is checked as a formula, since commands are recognised before expansion.
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
import traceback
import types
from collections.abc import Iterable
from dataclasses import dataclass
from types import ModuleType
from typing import TextIO

from dltl.evaluator import Evaluator, results_statistics
from dltl.log import Log
from dltl.macros import unfold_macros
from dltl.parser import parse_formula

COMMENT_PREFIX = ';'
SYSTEM_PREFIX = '@'
MACRO_PREFIX = '?'
BYE_COMMANDS = frozenset({'_BYE', '_AGUR', 'agur'})


@dataclass
class CheckSummary:
    """Result of checking one formula over every trace of the model."""
    formula: str
    yes: int        # traces satisfying the formula
    no: int         # traces not satisfying it
    pct: float      # percentage of satisfying traces
    seconds: float  # checking time

    def line(self) -> str:
        return f"{self.yes},{self.no},{self.pct},{self.seconds}"


class Session:
    def __init__(self, log: Log, props: ModuleType | None = None,
                 out: TextIO | None = None, err: TextIO | None = None):
        if props is None:
            from dltl import propositions as props
        if hasattr(props, 'COLUMNS'):
            props.COLUMNS = dict(log.column_index)
        self.log = log
        self.props = props
        self.evaluator = Evaluator(log.column_index, props)
        self.out = out if out is not None else sys.stdout
        self.err = err if err is not None else sys.stderr
        self.macros: dict[str, tuple[str, ...]] = {}
        self.results: dict[str, str] = {}        # id -> "id,1,0,1,..."
        self.count_results: dict[str, str] = {}  # id -> "id,0.5,0.0,1.0,..."
        self.checked_forms: list[str] = []
        self.loaded_modules: dict[str, str] = {}  # _LOAD name -> file
        self.cmd_clear_data()

        self._commands_0 = {
            '_INFO': self.cmd_info,
            '_WRITE': self.cmd_write,
            '_WRITE_LENGTHS': self.cmd_write_lengths,
            '_WHO': self.cmd_who,
            '_WHO_NOT': self.cmd_who_not,
            '_CLEAR_DATA': self.cmd_clear_data,
            '_CLEAR_CHECKED': self.cmd_clear_data,
        }
        self._commands_2 = {
            '_SET': self.cmd_set,
            '_RE': self.cmd_re,
            '_RANGE': self.cmd_range,
            '_LOAD': self.cmd_load,
        }

    # ------------------------------------------------------------------
    def run(self, lines: Iterable[str]) -> bool:
        """Execute lines until they run out or ``_AGUR`` is found.

        Returns ``False`` when the session was ended by ``_AGUR``.
        """
        for line in lines:
            if not self.execute(line):
                return False
        return True

    def execute(self, line: str) -> bool:
        """Execute one command or check one formula. Returns ``False`` on ``_BYE``."""
        line = line.strip()
        if not line or line.startswith(COMMENT_PREFIX):
            return True
        if line.startswith(SYSTEM_PREFIX):
            self.system_call(line[len(SYSTEM_PREFIX):])
            return True
        command, _, remainder = line.partition(' ')
        try:
            if command in BYE_COMMANDS:
                return False
            if command in self._commands_0:
                self._commands_0[command]()
            elif command in self._commands_2:
                name, _, args = remainder.strip().partition(' ')
                self._commands_2[command](name, args.strip())
            else:
                self.check_formula(line)
        except Exception as e:  # noqa: BLE001 - keep the session alive
            print(f"An error occurred: {e}", file=self.err)
            print("\n--- Full Traceback ---", file=self.err)
            traceback.print_exc(file=self.err)
            print("----------------------\n", file=self.err)
        return True

    # ------------------------------------------------------------------
    def check_formula(self, text: str) -> list[CheckSummary]:
        """Expand macros, then check every resulting formula over all the traces.

        One summary line ``yes,no,pct,seconds`` is printed per formula and the
        per-trace results are accumulated for ``_WRITE``.
        """
        summaries = []
        for formula in unfold_macros(text, self.macros):
            start = time.time()
            node = parse_formula(formula)
            if node is None:
                continue
            self.checked_forms.append(formula)
            yes = 0
            for tid in self.log.sorted_ids:
                res = self.evaluator.eval_formula(node, self.log.traces[tid])
                holds, _true_count, _false_count, ratio = results_statistics(res)
                yes += holds
                self.results[tid] += ',' + str(holds)
                self.count_results[tid] += ',' + str(ratio)
            n = self.log.n_traces
            summary = CheckSummary(formula, yes, n - yes, round(100 * yes / n, 2),
                                   round(time.time() - start, 2))
            print(summary.line(), file=self.out)
            summaries.append(summary)
        return summaries

    # ------------------------------------------------------------------
    # commands without arguments
    def cmd_info(self) -> None:
        print(self.log.info(), file=self.out)

    def cmd_write(self) -> None:
        self.log.save_results(self.results, self.count_results, self.checked_forms)

    def cmd_write_lengths(self) -> None:
        self.log.save_trace_lengths()

    def cmd_who(self) -> None:
        print(self.log.who(self.results), file=self.out)

    def cmd_who_not(self) -> None:
        print(self.log.who_not(self.results), file=self.out)

    def cmd_clear_data(self) -> None:
        for tid in self.log.sorted_ids:
            self.results[tid] = tid
            self.count_results[tid] = tid
        self.checked_forms.clear()

    # commands defining macros: _CMD ?name <args>
    def _check_macro_name(self, name: str) -> bool:
        if not name.startswith(MACRO_PREFIX):
            print(f"'{name}' is not acceptable as a macro name", file=self.err)
            print(f"The name of a macro must start with '{MACRO_PREFIX}'. Try ?{name}",
                  file=self.err)
            return False
        return True

    def cmd_set(self, name: str, values: str) -> None:
        """``_SET ?name a, b, c``"""
        if self._check_macro_name(name):
            self.macros[name] = tuple(a.strip() for a in values.split(','))

    def cmd_re(self, name: str, pattern: str) -> None:
        """``_RE ?name ac_.+`` : the atomic propositions matching the regex."""
        if self._check_macro_name(name):
            self.macros[name] = tuple(a for a in sorted(self.log.atomics)
                                      if re.fullmatch(pattern, a) is not None)

    def cmd_range(self, name: str, limits: str) -> None:
        """``_RANGE ?name from,to[,step]`` : integers from ``from`` to ``to`` inclusive."""
        if self._check_macro_name(name):
            parts = [int(x) for x in limits.split(',')]
            first, last = parts[0], parts[1]
            step = parts[2] if len(parts) > 2 else 1
            self.macros[name] = tuple(str(i) for i in range(first, last + 1, step))

    # loading of user code
    def cmd_load(self, name: str, path: str) -> None:
        """``_LOAD name file.py`` : load a Python file as module ``name``.

        Its functions and variables can then be used in data expressions as
        ``name.<attribute>``, like ``PROP.<attribute>`` for the default module.
        Loading the same name again replaces the module, so a file can be
        edited and reloaded in the middle of a session.
        """
        if not name.isidentifier():
            print(f"'{name}' is not a valid module name", file=self.err)
            return
        try:
            with open(path) as f:
                source = f.read()
        except OSError as e:
            print(f"Error: file '{path}' was not found ({e.strerror})", file=self.err)
            return
        # the source is executed directly (not imported) so that a reload
        # always sees the current content of the file
        module = types.ModuleType(name)
        module.__file__ = path
        exec(compile(source, path, 'exec'), module.__dict__)  # noqa: S102
        sys.modules[name] = module
        if hasattr(module, 'COLUMNS'):
            module.COLUMNS = dict(self.log.column_index)
        self.evaluator.add_module(name, module)
        self.loaded_modules[name] = path

    # system calls
    def system_call(self, command: str) -> int:
        """``@<command>`` : run ``command`` in the shell; returns its exit code."""
        self.out.flush()
        return subprocess.run(command, shell=True, check=False).returncode  # noqa: S602
