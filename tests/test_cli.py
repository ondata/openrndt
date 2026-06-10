"""Test CLI Typer end-to-end con HTTP mockato."""

from __future__ import annotations

import json

import httpx
import respx
from typer.testing import CliRunner

from openrndt.cli import app
from openrndt.config import DEFAULT_BASE_URL

runner = CliRunner()


@respx.mock
def test_cli_search_json(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["--format", "json", "search", "--q", "catasto", "--num", "2"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["total"] == 23580


@respx.mock
def test_cli_search_table(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["--format", "table", "search", "--num", "2"], env={"COLUMNS": "300"})
    assert result.exit_code == 0, result.output
    assert "RNDT" in result.output
    assert "Cartografia" in result.output or "Marsaglia" in result.output


@respx.mock
def test_cli_get_xml(item_response_xml):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA/xml").mock(
        return_value=httpx.Response(200, text=item_response_xml)
    )
    result = runner.invoke(app, ["get", "age:D_E973_MARSAGLIA", "--xml"])
    assert result.exit_code == 0, result.output
    assert "gmd:MD_Metadata" in result.stdout


@respx.mock
def test_cli_get_xml_and_html_mutually_exclusive():
    result = runner.invoke(app, ["get", "foo", "--xml", "--html"])
    assert result.exit_code != 0
    assert "non entrambi" in result.output


@respx.mock
def test_cli_get_not_found_shows_message():
    """ID inesistente (found:false) deve produrre exit 1 e messaggio leggibile."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/inesistente").mock(
        return_value=httpx.Response(200, json={"_id": "inesistente", "found": False})
    )
    result = runner.invoke(app, ["get", "inesistente"])
    assert result.exit_code == 1
    assert "non trovato" in result.output.lower()
    assert "inesistente" in result.output


def test_cli_base_url_override(monkeypatch):
    """Verifica che --base-url venga rispettato."""
    custom = "https://example.invalid/rndt"
    with respx.mock() as router:
        router.get(f"{custom}/rest/metadata/search").mock(
            return_value=httpx.Response(200, json={"total": 0, "num": 0, "start": 1, "results": []})
        )
        result = runner.invoke(app, ["--base-url", custom, "--format", "json", "search", "--q", "x"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["total"] == 0
