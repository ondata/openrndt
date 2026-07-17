"""Test diretti del dispatcher output.py — coprono rami non raggiungibili dalla CLI
(es. tabella/CSV con `table_rows` vuoto, che i comandi intercettano prima di chiamare `emit`)."""

from __future__ import annotations

import pytest

from openrndt import output


def test_set_mode_rejects_unknown_format():
    with pytest.raises(ValueError, match="non supportato"):
        output.set_mode("yaml")


def test_emit_csv_writes_rows(capsys):
    output.set_mode("csv")
    output.emit({}, table_rows=[{"a": "1", "b": "2"}, {"a": "3", "b": "4"}])
    out = capsys.readouterr().out
    assert out.splitlines() == ["a,b", "1,2", "3,4"]


def test_emit_csv_empty_rows_writes_nothing(capsys):
    output.set_mode("csv")
    output.emit({}, table_rows=[])
    out = capsys.readouterr().out
    assert out == ""


def test_emit_table_without_rows_falls_back_to_json(capsys):
    output.set_mode("table")
    output.emit({"k": "v"})
    out = capsys.readouterr().out
    assert "k" in out and "v" in out


def test_emit_table_with_empty_rows_shows_placeholder(capsys):
    output.set_mode("table")
    output.emit({}, table_rows=[])
    out = capsys.readouterr().out
    assert "nessun risultato" in out
