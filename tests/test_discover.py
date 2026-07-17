"""Test del comando discover — deve funzionare senza rete."""

from __future__ import annotations

import json

import respx
from typer.testing import CliRunner

from openrndt.cli import app
from openrndt.codelists import DATA_CATEGORIES, OUTPUT_FORMATS, SORT_VALUES

runner = CliRunner()


@respx.mock(assert_all_called=False)
def test_discover_all_json():
    result = runner.invoke(app, ["--format", "json", "discover"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {"data_categories", "sort_values", "output_formats", "search_params", "lucene_fields"}
    assert payload["data_categories"]["planningCadastre"]
    assert payload["sort_values"]["dateDescending"]
    assert payload["output_formats"]["json"]


@respx.mock(assert_all_called=False)
def test_discover_single_section():
    result = runner.invoke(app, ["--format", "json", "discover", "--what", "data_categories"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload == DATA_CATEGORIES


@respx.mock(assert_all_called=False)
def test_discover_all_table():
    result = runner.invoke(app, ["--format", "table", "discover"], env={"COLUMNS": "300"})
    assert result.exit_code == 0, result.output
    assert "planningCadastre" in result.output


@respx.mock(assert_all_called=False)
def test_discover_single_section_table():
    result = runner.invoke(app, ["--format", "table", "discover", "--what", "output_formats"])
    assert result.exit_code == 0, result.output
    assert "json" in result.output.lower()


@respx.mock(assert_all_called=False)
def test_discover_unknown_section():
    result = runner.invoke(app, ["discover", "--what", "nope"])
    assert result.exit_code != 0
    assert "sconosciuta" in result.output.lower() or "nope" in result.output


def test_codelists_module_constants_consistency():
    assert "planningCadastre" in DATA_CATEGORIES
    assert "dateDescending" in SORT_VALUES
    assert "json" in OUTPUT_FORMATS
