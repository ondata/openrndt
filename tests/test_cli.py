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
def test_cli_search_table_gis_profile(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(
        app,
        ["--format", "table", "search", "--profile", "gis", "--num", "2"],
        env={"COLUMNS": "300"},
    )
    assert result.exit_code == 0, result.output
    for header in ("type", "category", "org", "resources"):
        assert header in result.output


@respx.mock
def test_cli_search_csv_gis_profile(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["--format", "csv", "search", "--profile", "gis", "--num", "2"])
    assert result.exit_code == 0, result.output
    assert "id,title,type,category,org,updated,resources,bbox" in result.output


@respx.mock
def test_cli_search_csv_gis_profile_skips_partial_bbox():
    payload = {
        "total": 1,
        "num": 1,
        "start": 1,
        "results": [
            {
                "id": "x:1",
                "title": "T",
                "updated": "2026-01-01T00:00:00Z",
                "author": {"name": "csw.foo"},
                "_source": {"apiso_Type_s": "dataset", "apiso_OrganizationName_txt": "Org"},
                "bbox": {"xmin": 10, "xmax": 20},
                "links": [],
            }
        ],
    }
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(return_value=httpx.Response(200, json=payload))
    result = runner.invoke(app, ["--format", "csv", "search", "--profile", "gis", "--num", "1"])
    assert result.exit_code == 0, result.output
    assert result.output.splitlines()[1].endswith(",")


@respx.mock
def test_cli_search_csv_qgis_profile(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["--format", "csv", "search", "--profile", "qgis", "--num", "2"])
    assert result.exit_code == 0, result.output
    assert "id,title,type,category,org,updated,wms_url,wfs_url,download_url,xmin,ymin,xmax,ymax" in result.output


@respx.mock
def test_cli_search_profile_implies_table(search_response_json):
    """Senza --format, --profile porta da solo all'output tabellare."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["search", "--profile", "gis", "--num", "2"], env={"COLUMNS": "300"})
    assert result.exit_code == 0, result.output
    assert "RNDT" in result.output
    for header in ("type", "category", "org", "resources"):
        assert header in result.output


@respx.mock
def test_cli_search_without_profile_stays_json(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["search", "--q", "catasto", "--num", "2"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["total"] == 23580


@respx.mock
def test_cli_search_profile_with_explicit_json_warns(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["--format", "json", "search", "--profile", "gis", "--num", "2"])
    assert result.exit_code == 0, result.output
    assert "--profile è ignorato con --format json" in result.output
    assert json.loads(result.stdout)["total"] == 23580


@respx.mock
def test_cli_search_profile_with_explicit_compact_warns(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["--format", "compact", "search", "--profile", "gis", "--num", "2"])
    assert result.exit_code == 0, result.output
    assert "--profile è ignorato con --format compact" in result.output
    # l'avviso va su stderr: stdout resta NDJSON con le colonne di compact, non quelle del profilo
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert lines
    for line in lines:
        row = json.loads(line)
        assert set(row) == {"id", "title", "org", "type", "category", "updated", "resources"}


@respx.mock
def test_cli_search_profile_with_explicit_csv_does_not_warn(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["--format", "csv", "search", "--profile", "gis", "--num", "2"])
    assert result.exit_code == 0, result.output
    assert "Avviso" not in result.output


def test_cli_search_rejects_unknown_profile():
    result = runner.invoke(app, ["search", "--profile", "foo"])
    assert result.exit_code == 2
    assert "profilo non supportato" in result.output.lower()


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
    assert "suggerimenti" in result.output.lower()
    assert "wildcard" in result.output


@respx.mock
def test_cli_search_zero_results_json_hint_on_stderr():
    """search con 0 risultati in json: stdout solo JSON puro, suggerimenti su stderr."""
    empty = {"total": {"value": 0, "relation": "eq"}, "num": 0, "start": 1, "results": []}
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=empty)
    )
    result = runner.invoke(app, ["search", "--q", "zzz", "--bbox", "7,44,8,45"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == empty
    assert "nessun risultato" in result.stderr.lower()
    assert "suggerimenti" in result.stderr.lower()
    assert "bbox" in result.stderr.lower()


@respx.mock
def test_cli_search_sort_http_500_hint():
    """Sort non ordinabile → HTTP 500: messaggio con i campi ordinabili e rimando a discover."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(500, text="server error")
    )
    result = runner.invoke(app, ["search", "--q", "catasto", "--sort", "apiso_PublicationDate_dt:desc"])
    assert result.exit_code == 1, result.output
    assert "500" in result.output
    assert "apiso_Modified_dt" in result.output
    assert "discover" in result.output
    assert "Traceback" not in result.output


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


def test_cli_invalid_format_no_traceback():
    """--format con valore non supportato: messaggio leggibile, exit 2, nessuno stack trace."""
    result = runner.invoke(app, ["--format", "yaml", "search", "--q", "x"])
    assert result.exit_code == 2
    assert "non supportato" in result.output.lower()
    assert "Traceback" not in result.output


@respx.mock
def test_cli_get_json_success(item_response_json):
    """get senza flag (default json) su un ID esistente: payload completo su stdout."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA").mock(
        return_value=httpx.Response(200, json=item_response_json)
    )
    result = runner.invoke(app, ["get", "age:D_E973_MARSAGLIA"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == item_response_json


@respx.mock
def test_cli_get_html_success():
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA/html").mock(
        return_value=httpx.Response(200, text="<html><body>Marsaglia</body></html>")
    )
    result = runner.invoke(app, ["get", "age:D_E973_MARSAGLIA", "--html"])
    assert result.exit_code == 0, result.output
    assert "Marsaglia" in result.stdout


@respx.mock
def test_cli_get_table_success(item_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA").mock(
        return_value=httpx.Response(200, json=item_response_json)
    )
    result = runner.invoke(app, ["--format", "table", "get", "age:D_E973_MARSAGLIA"], env={"COLUMNS": "300"})
    assert result.exit_code == 0, result.output
    assert "MARSAGLIA" in result.output


@respx.mock
def test_cli_search_compact_zero_results_warns():
    """search con 0 risultati in compact: avviso su stderr, exit 0 (come csv/table)."""
    empty = {"total": 0, "num": 0, "start": 1, "results": []}
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=empty)
    )
    result = runner.invoke(app, ["--format", "compact", "search", "--q", "zzz"])
    assert result.exit_code == 0, result.output
    assert "nessun risultato" in result.output.lower()
    assert "suggerimenti" in result.output.lower()


@respx.mock
def test_cli_search_non_dict_payload_no_traceback():
    """Risposta 200 con JSON valido ma non un oggetto (es. una lista): messaggio leggibile, exit 1."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=["non", "un", "oggetto"])
    )
    result = runner.invoke(app, ["search", "--q", "x"])
    assert result.exit_code == 1, result.output
    assert "non è un oggetto json" in result.output.lower()
    assert "Traceback" not in result.output


@respx.mock
def test_cli_search_advanced_filters_build_expected_query():
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"total": 0, "num": 0, "start": 1, "results": []})
    )
    result = runner.invoke(
        app,
        [
            "search",
            "--q",
            "catasto",
            "--bbox",
            "7,44,8,45",
            "--bbox-crs",
            "CRS:84",
            "--updated-from",
            "2024-01-01",
            "--updated-to",
            "2024-12-31",
            "--published-from",
            "2020-01-01",
            "--published-to",
            "2020-12-31",
            "--num",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    params = dict(route.calls.last.request.url.params)
    assert params["bbox"] == "7,44,8,45"
    assert "apiso_Modified_dt:[2024-01-01T00:00:00Z TO 2024-12-31T23:59:59Z]" in params["q"]
    assert "apiso_PublicationDate_dt:[2020-01-01T00:00:00Z TO 2020-12-31T23:59:59Z]" in params["q"]


def test_cli_search_rejects_unsupported_bbox_crs():
    result = runner.invoke(app, ["search", "--bbox", "7,44,8,45", "--bbox-crs", "EPSG:3857"])
    assert result.exit_code == 2
    assert "non supportato" in result.output


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


@respx.mock
def test_cli_resources_json_with_check(item_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA").mock(
        return_value=httpx.Response(200, json=item_response_json)
    )
    respx.head(
        "https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"
    ).mock(return_value=httpx.Response(200))
    respx.head(
        "https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php?SERVICE=WFS&REQUEST=GetCapabilities&VERSION=2.0.0"
    ).mock(return_value=httpx.Response(503))
    respx.get(
        "https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php?SERVICE=WFS&REQUEST=GetCapabilities&VERSION=2.0.0"
    ).mock(return_value=httpx.Response(503))
    result = runner.invoke(app, ["resources", "age:D_E973_MARSAGLIA"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["id"] == "age:D_E973_MARSAGLIA"
    assert payload["checked"] is True
    assert payload["count"] == 2
    assert payload["resources"][0]["type"] == "WMS"
    assert payload["resources"][0]["ok"] is True
    assert payload["resources"][1]["type"] == "WFS"
    assert payload["resources"][1]["ok"] is False


@respx.mock
def test_cli_resources_no_check(item_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA").mock(
        return_value=httpx.Response(200, json=item_response_json)
    )
    result = runner.invoke(app, ["resources", "age:D_E973_MARSAGLIA", "--no-check"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["checked"] is False
    assert payload["count"] == 2
    assert "ok" not in payload["resources"][0]


@respx.mock
def test_cli_resources_batch_multiple_ids(item_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA").mock(
        return_value=httpx.Response(200, json=item_response_json)
    )
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/altro%3Aid").mock(
        return_value=httpx.Response(200, json=item_response_json)
    )
    result = runner.invoke(app, ["resources", "--no-check", "age:D_E973_MARSAGLIA", "altro:id"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["count"] == 2
    assert payload["checked"] is False
    assert len(payload["results"]) == 2
    assert payload["results"][0]["id"] == "age:D_E973_MARSAGLIA"
    assert payload["results"][0]["count"] == 2
    assert payload["results"][1]["id"] == "altro:id"


@respx.mock
def test_cli_resources_batch_collects_errors(item_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA").mock(
        return_value=httpx.Response(200, json=item_response_json)
    )
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/inesistente").mock(
        return_value=httpx.Response(200, json={"found": False})
    )
    result = runner.invoke(app, ["resources", "--no-check", "age:D_E973_MARSAGLIA", "inesistente"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["count"] == 2
    assert payload["results"][0]["id"] == "age:D_E973_MARSAGLIA"
    assert "error" in payload["results"][1]


@respx.mock
def test_cli_resources_not_found():
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/inesistente").mock(
        return_value=httpx.Response(200, json={"_id": "inesistente", "found": False})
    )
    result = runner.invoke(app, ["resources", "inesistente"])
    assert result.exit_code == 1
    assert "non trovato" in result.output.lower()


@respx.mock
def test_cli_footprints_geojson(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["footprints", "--q", "catasto", "--num", "2"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["type"] == "FeatureCollection"
    assert payload["crs"]["properties"]["name"] == "EPSG:4326"
    assert len(payload["features"]) == 2
    first = payload["features"][0]
    assert first["geometry"]["type"] == "Polygon"
    assert first["properties"]["id"] == "age:D_E973_MARSAGLIA"


@respx.mock
def test_cli_footprints_invalid_bbox_crs():
    result = runner.invoke(app, ["footprints", "--bbox", "7,44,8,45", "--bbox-crs", "EPSG:3857"])
    assert result.exit_code == 2
    assert "non supportato" in result.output
