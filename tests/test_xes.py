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
"""Direct loading of XES event logs (dltl.xes)."""
import gzip
import io
import shutil
from pathlib import Path

import pytest

from conftest import EXAMPLES, golden, result_lines
from dltl import Log, Session, load_xes
from dltl.cli import main, read_file
from dltl.xes import (
    Mapping,
    atomic_identifier,
    load_schema,
    safe_string,
    timestamp_milliseconds,
)

XES = """<?xml version="1.0" encoding="UTF-8"?>
<log xes.version="1.0" xmlns="http://www.xes-standard.org/">
  <global scope="event"><string key="concept:name" value="name"/></global>
  <string key="creator" value="test"/>
  <trace>
    <string key="concept:name" value="case 1.a"/>
    <string key="alias" value="first"/>
    <event>
      <string key="concept:name" value="Start activity"/>
      <date key="time:timestamp" value="2019-01-29T09:23:00.952+11:00"/>
      <int key="amount" value="10"/>
      <string key="note" value="a&amp;b, c;d=e"/>
    </event>
    <event>
      <string key="concept:name" value="123-test"/>
      <float key="ratio" value="0.5"/>
      <boolean key="ok" value="true"/>
      <id key="uid" value="event-7"/>
      <list key="roles">
        <values><string key="r" value="admin"/><int key="r" value="2"/></values>
      </list>
      <container key="who">
        <string key="name" value="John"/><int key="age" value="35"/>
      </container>
    </event>
  </trace>
  <trace>
    <event>
      <string key="concept:name" value="x+y"/>
      <int key="amount" value="3"/>
    </event>
  </trace>
</log>
"""


def write(tmp_path: Path, text: str, name: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def schema_file(tmp_path: Path, *entries: tuple[str, str], name="schema.xml") -> Path:
    body = "".join(f'<string key="{k}" value="{v}"/>' for k, v in entries)
    return write(tmp_path, f'<container key="mod:schema">{body}</container>', name)


# --- conversion rules -------------------------------------------------------

def test_atomic_identifier():
    assert atomic_identifier("Start activity") == "Start_activity"
    assert atomic_identifier("event-7") == "event_7"
    assert atomic_identifier("x+y") == "x_y"
    assert atomic_identifier("123-test") == "_123_test"
    assert atomic_identifier("a - b") == "a_b"
    assert atomic_identifier("") == "_"


def test_safe_string_replaces_only_the_separators():
    assert safe_string("A&B,C;D=E\tF\nG") == "A_B_C_D_E_F_G"
    assert safe_string("John Doe - Manager") == "John Doe - Manager"


def test_timestamp_milliseconds():
    assert timestamp_milliseconds("2019-01-29T09:23:00.952+11:00") == 1548714180952
    assert timestamp_milliseconds("1970-01-01T00:00:01Z") == 1000
    assert timestamp_milliseconds("1970-01-01T00:00:01") == 1000  # no zone: UTC
    with pytest.raises(ValueError, match="timestamp"):
        timestamp_milliseconds("yesterday")


# --- loading without a schema ----------------------------------------------

def test_default_mapping(tmp_path: Path):
    log = load_xes(write(tmp_path, XES, "log.xes"))
    # concept:name is atomic; the rest keep their name, in order of first
    # appearance, with a type derived from their XES type
    assert log.attrib_desc == ["aconcept:name", "ntime:timestamp", "namount", "snote",
                               "nratio", "bok", "auid", "@roles", "$who"]
    assert log.column_index == {"time:timestamp": 2, "amount": 3, "note": 4, "ratio": 5,
                                "ok": 6, "roles": 7, "who": 8}
    # trace ids are identifiers; a trace without concept:name is trace_<n>
    assert log.sorted_ids == ["case_1_a", "trace_1"]
    assert log.atomics == {"Start_activity", "_123_test", "x_y", "event_7", "_"}
    first, second = log.traces["case_1_a"]
    # attributes that appear later in the log are missing in the first event
    assert first == (1, {"Start_activity", "_"}, 1548714180952.0, 10.0, "a_b_ c_d_e",
                     0.0, False, {""}, {})
    assert second == (2, {"_123_test", "event_7"}, 0.0, 0.0, "",
                      0.5, True, {"admin", "2"}, {"name": "John", "age": 35.0})
    assert log.traces["trace_1"] == ((1, {"x_y", "_"}, 0.0, 3.0, "", 0.0, False, {""}, {}),)


def test_path_and_info(tmp_path: Path):
    p = write(tmp_path, XES, "log.xes")
    log = load_xes(p)
    assert log.path == str(tmp_path / "log")  # result files go next to the log
    assert f"file:      {p}" in log.info()
    assert "#traces:   2" in log.info() and "#events:   3" in log.info()


def test_log_load_reads_xes(tmp_path: Path):
    p = write(tmp_path, XES, "log.xes")
    assert Log.load(p) == load_xes(p)
    assert Log.load(str(p)) == load_xes(p)


def test_gzipped_log(tmp_path: Path):
    plain = load_xes(write(tmp_path, XES, "log.xes"))
    gz = tmp_path / "other.XES.gz"
    with gzip.open(gz, "wt", encoding="utf-8") as f:
        f.write(XES)
    log = Log.load(gz)
    assert log.traces == plain.traces and log.attrib_desc == plain.attrib_desc
    assert log.path == str(tmp_path / "other")
    assert log.source == str(gz)


def test_missing_dictionary_is_silent(tmp_path: Path, capsys):
    load_xes(write(tmp_path, XES, "log.xes"))
    assert capsys.readouterr().err == ""


# --- mapping schema ---------------------------------------------------------

def test_schema_types_names_and_order(tmp_path: Path):
    schema = schema_file(tmp_path, ("concept:name", "aActivity"), ("amount", "sAmount"),
                         ("time:timestamp", "nTime"), ("uid", "sUid"), ("absent", "nAbsent"))
    log = load_xes(write(tmp_path, XES, "log.xes"), schema=schema)
    # schema entries first, in their order; then the attributes it does not mention
    assert log.attrib_desc == ["aActivity", "sAmount", "nTime", "sUid", "nAbsent",
                               "snote", "nratio", "bok", "@roles", "$who"]
    first, second = log.traces["case_1_a"]
    assert first[:7] == (1, {"Start_activity"}, "10", 1548714180952.0, "", 0.0, "a_b_ c_d_e")
    assert second[4] == "event-7"  # a string keeps its characters, an atomic does not
    assert log.atomics == {"Start_activity", "_123_test", "x_y"}


def test_ignore_keeps_only_the_schema(tmp_path: Path):
    schema = schema_file(tmp_path, ("concept:name", "aActivity"), ("amount", "nAmount"))
    log = load_xes(write(tmp_path, XES, "log.xes"), schema=schema, ignore=True)
    assert log.attrib_desc == ["aActivity", "nAmount"]
    assert log.traces["trace_1"] == ((1, {"x_y"}, 3.0),)
    assert load_xes(tmp_path / "log.xes", ignore=True).attrib_desc == ["aconcept:name"]


def test_trace_id_key(tmp_path: Path):
    log = load_xes(write(tmp_path, XES, "log.xes"), trace_id_key="alias")
    assert log.sorted_ids == ["first", "trace_1"]


def test_traces_with_the_same_id_are_one_trace(tmp_path: Path):
    xes = ('<log><trace><string key="concept:name" value="t"/>'
           '<event><string key="concept:name" value="a"/></event></trace>'
           '<trace><string key="concept:name" value="t"/>'
           '<event><string key="concept:name" value="b"/></event></trace></log>')
    log = load_xes(write(tmp_path, xes, "log.xes"))
    assert log.traces == {"t": ((1, {"a"}), (2, {"b"}))}


def test_load_schema(tmp_path: Path):
    assert load_schema(schema_file(tmp_path, ("concept:name", "aE"), ("p", "$p"))) == \
        [Mapping("concept:name", "a", "E"), Mapping("p", "$", "p")]
    # the container may be anywhere in the XML file
    embedded = write(tmp_path, '<log><container key="mod:schema">'
                               '<string key="k" value="nK"/></container></log>', "e.xml")
    assert load_schema(embedded) == [Mapping("k", "n", "K")]


@pytest.mark.parametrize("text, message", [
    ("<container key='other'/>", "not found"),
    ("<container key='mod:schema'/>", "empty"),
    ("<container key='mod:schema'><string key='k' value='xK'/></container>", "Invalid"),
    ("<container key='mod:schema'><string key='k' value='n'/></container>", "Invalid"),
    ("<container key='mod:schema'><int key='k' value='1'/></container>", "Only <string>"),
    ("<container key='mod:schema'><string value='nK'/></container>", "without an XES key"),
    ("<container key='mod:schema'><string key='k' value='nK'/>"
     "<string key='k' value='sJ'/></container>", "Duplicate XES attribute"),
    ("<container key='mod:schema'><string key='k' value='nK'/>"
     "<string key='j' value='sK'/></container>", "Duplicate attribute"),
    ("<container key='mod:schema'>", "Invalid XML schema"),
])
def test_invalid_schemas(tmp_path: Path, text: str, message: str):
    with pytest.raises(ValueError, match=message):
        load_schema(write(tmp_path, text, "bad.xml"))


def test_name_clash_between_schema_and_log(tmp_path: Path):
    # 'amount' of the log would be a second attribute called 'amount'
    schema = schema_file(tmp_path, ("concept:name", "aE"), ("ratio", "namount"))
    with pytest.raises(ValueError, match="Duplicate attribute 'namount'"):
        load_xes(write(tmp_path, XES, "log.xes"), schema=schema)


@pytest.mark.parametrize("event, message", [
    ('<int key="n" value="many"/>', "Invalid integer"),
    ('<float key="n" value="inf"/>', "Non-finite"),
    ('<date key="d" value="today"/>', "timestamp"),
    ('<boolean key="b" value="maybe"/>', "boolean"),
    ('<string value="no key"/>', "no key"),
    ('<list key="l"><list key="m"/></list>', "Nested"),
])
def test_invalid_values(tmp_path: Path, event: str, message: str):
    xes = f"<log><trace><event>{event}</event></trace></log>"
    with pytest.raises(ValueError, match=message):
        load_xes(write(tmp_path, xes, "log.xes"))


def test_value_that_does_not_fit_the_schema_type(tmp_path: Path):
    schema = schema_file(tmp_path, ("concept:name", "nName"))
    with pytest.raises(ValueError, match="Unable to convert"):
        load_xes(write(tmp_path, XES, "log.xes"), schema=schema)


@pytest.mark.parametrize("value", ["inf", "-inf", "nan"])
def test_non_finite_string_for_a_number(tmp_path: Path, value: str):
    schema = schema_file(tmp_path, ("concept:name", "aE"), ("size", "nSize"))
    xes = f'<log><trace><event><string key="size" value="{value}"/></event></trace></log>'
    with pytest.raises(ValueError, match="Non-finite number for 'size'"):
        load_xes(write(tmp_path, xes, "log.xes"), schema=schema)


def test_invalid_or_missing_log(tmp_path: Path):
    with pytest.raises(ValueError, match="Invalid XES file"):
        load_xes(write(tmp_path, "<log><trace>", "broken.xes"))
    with pytest.raises(OSError):
        load_xes(tmp_path / "missing.xes")


# --- the sample model as an XES log ------------------------------------------

def test_sample_xes_is_the_sample_model(sample_dir: Path):
    mod = Log.load(sample_dir / "sample")
    xes = load_xes(sample_dir / "sample.xes", schema=sample_dir / "sample.schema.xml")
    assert xes.attrib_desc == mod.attrib_desc + ["nTime", "sResource"]
    assert xes.sorted_ids == mod.sorted_ids and xes.atomics == mod.atomics
    assert xes.path == mod.path
    n = len(mod.traces["id0"][0])
    for tid in ("id0", "id1"):
        assert [e[:n] for e in xes.traces[tid]] == list(mod.traces[tid])
    # the only difference: '=' cannot be part of an item of a set
    assert [e[:n] for e in xes.traces["id2"][:-1]] == list(mod.traces["id2"][:-1])
    assert mod.traces["id2"][-1][3] == {"z", "input=kkkkkkk", "99", "Mundo"}
    assert xes.traces["id2"][-1][3] == {"z", "input_kkkkkkk", "99", "Mundo"}
    assert xes.traces["id0"][0][n:] == (1709539200000.0, "Ana")


def test_sample_xes_reproduces_the_golden_session(sample_dir: Path):
    log = load_xes(sample_dir / "sample.xes", schema=sample_dir / "sample.schema.xml")
    out = io.StringIO()
    session = Session(log, out=out, err=io.StringIO())
    assert session.run(read_file(sample_dir / "sample.init"))
    assert not session.run(read_file(sample_dir / "formulas.txt"))  # ends with _BYE
    assert result_lines(out.getvalue()) == golden("sample.stdout").split()
    for suffix in (".res", ".norm", ".forms"):
        assert (sample_dir / f"sample{suffix}").read_text() == golden(f"sample{suffix}")


def test_data_expressions_on_xes_attributes(sample_dir: Path):
    out = io.StringIO()
    schema = sample_dir / "sample.schema.xml"
    session = Session(load_xes(sample_dir / "sample.xes", schema=schema), out=out)
    session.execute('F x.(a & X F y.(b & "(x,y)y[Time] - x[Time] <= 60000"))')
    session.execute("_WHO")
    # without a schema the attribute keeps its XES name, which is reached through COL
    session = Session(Log.load(sample_dir / "sample.xes"), out=out)
    session.execute("F x.(a & X F y.(b & "
                    "\"(x,y)y[COL['time:timestamp']] - x[COL['time:timestamp']] <= 60000\"))")
    assert out.getvalue().splitlines()[:2] == ["1,2,33.33,0.0", "id1 "]
    assert out.getvalue().splitlines()[2] == "1,2,33.33,0.0"


# --- a real log: examples/xes-example -------------------------------------------

XES_EXAMPLE = EXAMPLES / "xes-example"


def xes_example_dir(tmp_path: Path) -> Path:
    """A copy of the example, so that nothing is written in the repository."""
    return Path(shutil.copytree(XES_EXAMPLE, tmp_path / "xes-example"))


def test_xes_example_model(tmp_path: Path):
    d = xes_example_dir(tmp_path)
    log = load_xes(d / "xes-example.xes", schema=d / "xes-example.schema.xml")
    assert (log.n_traces, log.n_events, len(log.atomics)) == (20, 1394, 738)
    assert log.column_index == {"timestamp": 2, "ROUND": 3, "ACTIVITY": 4, "STAGE": 5,
                                "VIDEOSTART": 6, "VIDEOEND": 7}
    assert log.traces["_1539302414925_video_1_3_CVC"][0] == \
        (1, {"Hand_washing", "start", "R_13_1C", "_1539301115461"}, 1539259200000.0, "Pre",
         "Hand washing", "Operator and Patient Preparation", 55.0, 67.0)
    # without the schema only the activity is atomic and the video positions are strings
    plain = Log.load(d / "xes-example.xes")
    assert len(plain.atomics) == 29
    assert plain.traces["_1539302414925_video_1_3_CVC"][0][-2:] == ("55", "67")


def test_xes_example_matches_golden(tmp_path: Path, capsys):
    d = xes_example_dir(tmp_path)
    code = main(["--log-file", str(d / "xes-example.xes"),
                 "--xes-schema", str(d / "xes-example.schema.xml"),
                 "--formula-file", str(d / "formulas.txt"), "--no-interactive"])
    assert code == 0
    assert result_lines(capsys.readouterr().out) == golden("xes-example.stdout").split()


# --- command line -------------------------------------------------------------

def test_cli_checks_an_xes_log(sample_dir: Path, capsys):
    formulas = sample_dir / "f.txt"
    formulas.write_text('F x.("(x)x[V] == 10")\n_WRITE\n')
    code = main(["--log-file", str(sample_dir / "sample.xes"),
                 "--xes-schema", str(sample_dir / "sample.schema.xml"),
                 "--formula-file", str(formulas), "--no-interactive"])
    out = capsys.readouterr().out
    assert code == 0
    assert f"file:      {sample_dir / 'sample.xes'}" in out
    assert "att. desc: ['aE', 'nV', '@att', '$p', 'nTime', 'sResource']" in out
    assert result_lines(out) == ["2,1,66.67"]
    assert (sample_dir / "sample.res").read_text() == "id0,0\nid1,1\nid2,1\n"


def test_cli_xes_options(sample_dir: Path, capsys):
    xes = str(sample_dir / "sample.xes")
    empty = sample_dir / "empty.txt"
    empty.write_text("")
    common = ["--formula-file", str(empty), "--no-interactive"]
    assert main(["--log-file", xes, "--xes-ignore", *common]) == 0
    assert "att. desc: ['aconcept:name']" in capsys.readouterr().out
    # a schema with two of the six attributes: only those two with --xes-ignore, all without it
    schema = str(schema_file(sample_dir, ("concept:name", "aE"), ("V", "nValue")))
    assert main(["--log-file", xes, "--xes-schema", schema, "--xes-ignore", *common]) == 0
    assert "att. desc: ['aE', 'nValue']" in capsys.readouterr().out
    assert main(["--log-file", xes, "--xes-schema", schema, *common]) == 0
    assert ("att. desc: ['aE', 'nValue', '@att', '$p', 'ntime:timestamp', 'sorg:resource']"
            in capsys.readouterr().out)
    assert main(["--log-file", xes, "--xes-trace-id-key", "none", *common]) == 0
    assert "#traces:   3" in capsys.readouterr().out  # trace_0, trace_1, trace_2
    # legacy syntax for the model, new options for XES
    assert main([f"log-file={xes}", "--xes-ignore", f"formula-file={empty}",
                 "interactive=false"]) == 0


def test_cli_xes_errors(sample_dir: Path, capsys):
    xes = str(sample_dir / "sample.xes")
    assert main(["--log-file", xes, "--xes-schema", str(sample_dir / "nope.xml")]) == 1
    assert "cannot read" in capsys.readouterr().err
    assert main(["--log-file", xes, "--xes-schema", str(sample_dir / "sample.init")]) == 1
    assert "Invalid XML schema" in capsys.readouterr().err
    assert main(["--log-file", str(sample_dir / "missing.xes")]) == 1
    # the XES options make no sense with a .mod model
    with pytest.raises(SystemExit) as e:
        main(["--log-file", str(sample_dir / "sample"), "--xes-ignore"])
    assert e.value.code == 2
    assert "--xes-*" in capsys.readouterr().err
