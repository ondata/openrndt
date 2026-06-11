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
def test_cli_search_compact_ndjson(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["--format", "compact", "search", "--q", "catasto", "--num", "2"])
    assert result.exit_code == 0, result.output
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    assert len(lines) == 2  # una riga JSON per record
    first = json.loads(lines[0])
    assert first["id"] == "age:D_E973_MARSAGLIA"
    assert first["org"] == "Agenzia delle Entrate"
    assert first["resources"] == ["WFS", "WMS"]


@respx.mock
def test_cli_get_compact_rejected():
    result = runner.invoke(app, ["--format", "compact", "get", "age:D_E973_MARSAGLIA"])
    assert result.exit_code == 1
    assert "non è tabellare" in result.output


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
    """ID inesistente (found:false): exit 1 e messaggio leggibile, nessun JSON su stdout."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/inesistente").mock(
        return_value=httpx.Response(200, json={"_id": "inesistente", "found": False})
    )
    result = runner.invoke(app, ["get", "inesistente"])
    assert result.exit_code == 1
    assert "non trovato" in result.output.lower()
    assert "inesistente" in result.output


@respx.mock
def test_cli_get_xml_not_found_shows_message():
    """--xml con ID inesistente: il server risponde 500, exit 1 con messaggio HTTP."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/inesistente/xml").mock(
        return_value=httpx.Response(500, json={"error": {"message": "NullPointerException"}})
    )
    result = runner.invoke(app, ["get", "inesistente", "--xml"])
    assert result.exit_code == 1
    assert "500" in result.output


@respx.mock
def test_cli_get_html_not_found_shows_message():
    """--html con ID inesistente: il server risponde 501, exit 1 con messaggio HTTP."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/inesistente/html").mock(
        return_value=httpx.Response(501)
    )
    result = runner.invoke(app, ["get", "inesistente", "--html"])
    assert result.exit_code == 1
    assert "501" in result.output


@respx.mock
def test_cli_search_connect_error_no_traceback():
    """Errore di rete (connessione rifiutata): messaggio leggibile, exit 1, nessuno stack trace."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    result = runner.invoke(app, ["search", "--q", "x"])
    assert result.exit_code == 1
    assert "rete" in result.output.lower()
    assert "Traceback" not in result.output


@respx.mock
def test_cli_search_zero_results_csv_warns():
    """search con 0 risultati in CSV: avviso su stderr, exit 0, niente output vuoto silenzioso."""
    empty = {"total": 0, "num": 0, "start": 1, "results": []}
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=empty)
    )
    result = runner.invoke(app, ["--format", "csv", "search", "--q", "zzz"])
    assert result.exit_code == 0, result.output
    assert "nessun risultato" in result.output.lower()


@respx.mock
def test_cli_search_malformed_json_no_traceback():
    """Body non-JSON con status 200: messaggio leggibile, exit 1 (non 2), nessuno stack trace."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, text="<html>boom</html>")
    )
    result = runner.invoke(app, ["search", "--q", "x"])
    assert result.exit_code == 1, result.output
    assert "inattesa" in result.output.lower()
    assert "Traceback" not in result.output


@respx.mock
def test_cli_get_malformed_json_no_traceback():
    """get con body non-JSON e status 200: messaggio leggibile, exit 1, nessuno stack trace."""
    respx.get(url__regex=rf"{DEFAULT_BASE_URL}/rest/metadata/item/.*").mock(
        return_value=httpx.Response(200, text="<html>boom</html>")
    )
    result = runner.invoke(app, ["get", "foo"])
    assert result.exit_code == 1, result.output
    assert "inattesa" in result.output.lower()
    assert "Traceback" not in result.output


def test_cli_search_invalid_num_no_traceback():
    """Parametro fuori range (num > 5000): messaggio leggibile, exit 2, nessuno stack trace."""
    result = runner.invoke(app, ["search", "--num", "6000"])
    assert result.exit_code == 2
    assert "5000" in result.output
    assert "Traceback" not in result.output


def test_cli_get_csv_not_tabular():
    """get --format csv: dettaglio non tabellare → messaggio esplicito, exit 1, nessuna rete."""
    result = runner.invoke(app, ["--format", "csv", "get", "foo"])
    assert result.exit_code == 1
    assert "tabellare" in result.output.lower()


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
