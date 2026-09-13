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
Command-line interface of the model checker.

    dltl-mc --log-file <model> [--init-file F] [--formula-file F]
            [--no-interactive] [--multi-line] [--propositions F.py]

The legacy ``key=value`` syntax is also accepted:

    python MC.py log-file=<model> init-file=F formula-file=F interactive=false
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import time
from collections.abc import Iterator
from types import ModuleType
from typing import TextIO

from dltl import __version__
from dltl.log import Log
from dltl.session import Session

PROMPT = "DLTL -> "
MULTI_LINE_END = '$'

_LEGACY_ARG = re.compile(
    r'(log-file|init-file|formula-file|interactive|multi-line|propositions)=(.*)')


def normalize_legacy_argv(argv: list[str]) -> list[str]:
    """Translate ``key=value`` arguments into their ``--key value`` form."""
    out: list[str] = []
    for arg in argv:
        m = _LEGACY_ARG.fullmatch(arg)
        if not m:
            out.append(arg)
            continue
        key, value = m.groups()
        if key == 'interactive':
            out.append('--no-interactive' if value.strip().lower() == 'false' else '--interactive')
        elif key == 'multi-line':
            if value.strip().lower() == 'true':
                out.append('--multi-line')
        else:
            out += [f'--{key}', value]
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dltl-mc",
        description="Model checker for DLTL formulas over the traces of a .mod file.",
        epilog="The legacy syntax key=value (e.g. log-file=model interactive=false) "
               "is also accepted.")
    p.add_argument('--log-file', required=True, metavar='MODEL',
                   help="trace model, with or without the .mod suffix")
    p.add_argument('--init-file', metavar='FILE',
                   help="file with commands executed before reading formulas")
    p.add_argument('--formula-file', metavar='FILE',
                   help="file with the formulas to check (default: standard input)")
    p.add_argument('--propositions', metavar='FILE.py',
                   help="Python file with the user propositions available as PROP "
                        "(default: dltl.propositions)")
    p.add_argument('--interactive', action=argparse.BooleanOptionalAction, default=True,
                   help="show a prompt when reading formulas from standard input")
    p.add_argument('--multi-line', action='store_true',
                   help=f"formulas may span several lines and end with '{MULTI_LINE_END}'")
    p.add_argument('--version', action='version', version=f"%(prog)s {__version__}")
    return p


# ---------------------------------------------------------------------------
# input readers

def read_lines(stream: TextIO, prompt: str = "", multi_line: bool = False) -> Iterator[str]:
    """Yield formulas/commands from ``stream``, one per line or, in multi-line
    mode, joining lines until one containing ``$``."""
    buffer: list[str] = []
    while True:
        if prompt:
            print(prompt, end='', flush=True)
        line = stream.readline()
        if line == '':  # EOF
            if buffer:
                yield ''.join(buffer)
            if prompt:
                print("EOF found when reading formula", file=sys.stderr)
            return
        line = line.rstrip('\n')
        if not multi_line:
            yield line
        elif MULTI_LINE_END in line:
            buffer.append(line.split(MULTI_LINE_END)[0])
            yield ''.join(buffer)
            buffer = []
        else:
            buffer.append(line)


def read_file(path: str, multi_line: bool = False) -> Iterator[str]:
    with open(path) as f:
        yield from read_lines(f, multi_line=multi_line)


def load_propositions(path: str | None) -> ModuleType:
    if path is None:
        from dltl import propositions
        return propositions
    spec = importlib.util.spec_from_file_location("user_propositions", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load propositions from '{path}'")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    parser = build_parser()
    if not argv:
        parser.print_help(sys.stderr)
        return 2
    args = parser.parse_args(normalize_legacy_argv(argv))

    for path in (args.init_file, args.formula_file, args.propositions):
        if path is not None:
            try:
                open(path).close()
            except OSError as e:
                print(f"Error: cannot read '{path}': {e.strerror}", file=sys.stderr)
                return 1

    try:
        props = load_propositions(args.propositions)
        start = time.time()
        log = Log.load(args.log_file)
        loading_time = time.time() - start
    except (OSError, ValueError, ImportError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    session = Session(log, props)
    if args.interactive:
        print(f"Loading time: {loading_time:.4f} seconds")
    print(log.info())

    if args.init_file and not session.run(read_file(args.init_file)):
        return 0

    if args.formula_file:
        lines = read_file(args.formula_file, multi_line=args.multi_line)
    else:
        prompt = PROMPT if args.interactive else ""
        lines = read_lines(sys.stdin, prompt=prompt, multi_line=args.multi_line)
    session.run(lines)
    return 0
