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
from pathlib import Path

import pytest

from dltl.log import I_ATOM, I_POS, Log, cast, cast_format


def write_mod(tmp_path: Path, text: str, name="m") -> Path:
    p = tmp_path / f"{name}.mod"
    p.write_text(text)
    return p


def test_load_sample(sample_dir: Path):
    log = Log.load(sample_dir / "sample")
    assert log.n_traces == 3
    assert log.n_events == 17
    assert log.sorted_ids == ["id0", "id1", "id2"]
    assert log.atomics == {"a", "b", "c", "z"}
    assert log.column_index == {"V": 2, "att": 3, "p": 4}
    assert log.attrib_desc == ["aE", "nV", "@att", "$p"]
    assert log.trace_lengths == {"id0": 2, "id1": 8, "id2": 7}
    first = log.traces["id0"][0]
    assert first == (1, {"a"}, 4.0, {"a", "1"}, {"a": 1.0, "b": 2.0})
    assert first[I_POS] == 1 and first[I_ATOM] == {"a"}
    # positions restart at 1 in every trace
    assert [e[I_POS] for e in log.traces["id1"]] == list(range(1, 9))


def test_load_accepts_mod_suffix(sample_dir: Path):
    a = Log.load(sample_dir / "sample")
    b = Log.load(sample_dir / "sample.mod")
    assert a == b
    assert a.path == str(sample_dir / "sample")


def test_every_attribute_type_and_defaults(tmp_path: Path):
    p = write_mod(tmp_path, "aA,nN,bB,sS,@Q,$D,aA2\n"
                            "t1,x&3&true&hello&u;v&k=1;s=str;f=false&y\n"
                            "t1,x&&&&&&z\n")
    log = Log.load(p)
    assert log.column_index == {"N": 2, "B": 3, "S": 4, "Q": 5, "D": 6}
    e1, e2 = log.traces["t1"]
    assert e1 == (1, {"x", "y"}, 3.0, True, "hello", {"u", "v"},
                  {"k": 1.0, "s": "str", "f": False})
    assert e2[I_POS] == 2 and e2[I_ATOM] == {"x", "z"}
    assert e2[2] == 0 and e2[3] is False and e2[4] == ""
    assert e2[5] == {""} and e2[6] == {}


def test_column_numbering_skips_atomics(tmp_path: Path):
    p = write_mod(tmp_path, "aA,nN1,aB,sS2,nN3\nt,x&1&y&s&2\n")
    log = Log.load(p)
    assert log.column_index == {"N1": 2, "S2": 3, "N3": 4}
    assert log.traces["t"][0] == (1, {"x", "y"}, 1.0, "s", 2.0)


def test_two_logs_in_one_process_are_independent(tmp_path: Path):
    a = Log.load(write_mod(tmp_path, "aA,nN\nt,x&1\n", "a"))
    b = Log.load(write_mod(tmp_path, "aA,sS,nN\nt,x&s&2\n", "b"))
    assert a.column_index == {"N": 2}
    assert b.column_index == {"S": 2, "N": 3}


def test_unknown_attribute_type(tmp_path: Path):
    with pytest.raises(ValueError, match="Unknown attribute type"):
        Log.load(write_mod(tmp_path, "aA,zZ\nt,x&1\n"))


def test_wrong_number_of_values(tmp_path: Path):
    with pytest.raises(ValueError, match="line 2"):
        Log.load(write_mod(tmp_path, "aA,nN\nt,x\n"))


def test_load_compressed_model(tmp_path: Path, sample_dir: Path):
    import gzip
    data = (sample_dir / "sample.mod").read_bytes()
    with gzip.open(tmp_path / "zipped.mod.gz", "wb") as f:
        f.write(data)
    plain = Log.load(sample_dir / "sample")
    for name in ("zipped.mod.gz", "zipped.mod", "zipped"):
        log = Log.load(tmp_path / name)
        assert log.traces == plain.traces and log.column_index == plain.column_index
        assert log.path == str(tmp_path / "zipped")


def test_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        Log.load(tmp_path / "nope")


def test_cast():
    assert cast("true") is True and cast("False") is False
    assert cast(" 3 ") == 3.0 and cast("2.5") == 2.5
    assert cast("abc") == "abc"


def test_cast_format(capsys):
    assert cast_format("", "n") == 0 and cast_format("7", "n") == 7.0
    assert cast_format("abc", "n") == 0.0
    assert "not a number" in capsys.readouterr().err
    assert cast_format("TRUE", "b") is True and cast_format("", "b") is False
    assert cast_format("maybe", "b") is False
    assert cast_format(" s ", "s") == "s"


def test_info_who_and_save(sample_dir: Path):
    log = Log.load(sample_dir / "sample")
    assert "#traces:   3" in log.info()
    results = {"id0": "id0,1,0", "id1": "id1,0,1", "id2": "id2,1,1"}
    assert log.who(results) == "id1 id2 "
    assert log.who_not(results) == "id0 "
    log.save_results(results, {"id0": "id0,0.5", "id1": "id1,1.0", "id2": "id2,0.0"}, ["f1"])
    assert (sample_dir / "sample.res").read_text() == "id0,1,0\nid1,0,1\nid2,1,1\n"
    assert (sample_dir / "sample.norm").read_text() == "id0,0.5\nid1,1.0\nid2,0.0\n"
    assert (sample_dir / "sample.forms").read_text() == "f1\n"
    path = log.save_trace_lengths()
    assert Path(path).read_text() == "id0,2\nid1,8\nid2,7\n"
