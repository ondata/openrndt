"""Test CLI Typer end-to-end con HTTP mockato."""

from __future__ import annotations

import json
import re

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
    assert "id,title,type,category,org,updated,indexed,open,license,url,geolibre_url,resources,bbox" in result.output


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
    assert "id,title,type,category,org,updated,indexed,open,license,url,geolibre_url,wms_url,wfs_url,download_url,xmin,ymin,xmax,ymax" in result.output


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
        assert set(row) == {
                "id",
                "title",
                "org",
                "type",
                "category",
                "updated",
                "indexed",
                "open",
                "license",
                "url",
                "geolibre_url",
                "resources",
                "email",
                "download",
            }


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
    out = json.loads(result.stdout)
    assert out.pop("geolibre_search")["url"].endswith("&rndt=zzz&rndtBbox=7,44,8,45")
    assert out == empty
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
def test_cli_get_raw_success(item_response_json):
    """get --raw restituisce la busta Elasticsearch com'era prima della normalizzazione."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA").mock(
        return_value=httpx.Response(200, json=item_response_json)
    )
    result = runner.invoke(app, ["get", "age:D_E973_MARSAGLIA", "--raw"])
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


AE_CAPS = "https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php?SERVICE=WMS&REQUEST=GetCapabilities"
AE_CAPS_XML = """<WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms"><Capability>
<Layer><CRS>EPSG:6706</CRS><Layer><Name>CP.CadastralParcel</Name><Title>Particelle</Title></Layer></Layer>
</Capability></WMS_Capabilities>"""


@respx.mock
def test_cli_resources_layers_json(item_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA").mock(
        return_value=httpx.Response(200, json=item_response_json)
    )
    caps = respx.get(AE_CAPS).mock(return_value=httpx.Response(200, text=AE_CAPS_XML))
    head = respx.head(url__regex=r".*").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["resources", "age:D_E973_MARSAGLIA", "--layers"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    # --layers sostituisce il controllo di raggiungibilità
    assert payload["checked"] is False and not head.called
    assert caps.call_count == 1
    (layer,) = payload["layers"]
    assert (layer["name"], layer["title"], layer["crs"]) == ("CP.CadastralParcel", "Particelle", "EPSG:6706")
    assert layer["geolibre_url"].endswith("&rndtLayer=age%3AD_E973_MARSAGLIA~wms~CP.CadastralParcel")


@respx.mock
def test_cli_resources_layers_bare_uuid_links_resolved_id(item_response_json, monkeypatch):
    # get_item risolve l'UUID nudo; i link devono portare l'id risolto, che il plugin sa aprire
    monkeypatch.setattr("openrndt.cli.get_item", lambda item_id: item_response_json)
    respx.get(AE_CAPS).mock(return_value=httpx.Response(200, text=AE_CAPS_XML))
    result = runner.invoke(app, ["resources", "D_E973_MARSAGLIA", "--layers"])
    assert result.exit_code == 0, result.output
    (layer,) = json.loads(result.stdout)["layers"]
    assert "rndt=age%3AD_E973_MARSAGLIA&" in layer["geolibre_url"]


@respx.mock
def test_cli_resources_layers_csv_batch(item_response_json):
    respx.get(url__regex=rf"{DEFAULT_BASE_URL}/rest/metadata/item/.*").mock(
        return_value=httpx.Response(200, json=item_response_json)
    )
    respx.get(AE_CAPS).mock(return_value=httpx.Response(200, text=AE_CAPS_XML))
    result = runner.invoke(app, ["--format", "csv", "resources", "a:1", "b:2", "--layers"])
    assert result.exit_code == 0, result.output
    lines = result.stdout.strip().splitlines()
    assert lines[0] == "id,service,name,title,crs,geolibre_url,note,error"
    assert len(lines) == 3


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


@respx.mock
def test_cli_search_org_builds_contains_clause(search_response_json):
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["search", "--org", "comune di torino", "--num", "2"])
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.url.params["q"] == 'EnteResponsabile_s:/.*[cC][oO][mM][uU][nN][eE] [dD][iI] [tT][oO][rR][iI][nN][oO].*/'


@respx.mock
def test_cli_search_org_and_org_exact_together_exit_2(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["search", "--org", "a", "--org-exact", "b"])
    assert result.exit_code == 2
    assert "non entrambi" in result.output


@respx.mock
def test_cli_search_org_zero_results_suggests_catalog_names():
    """Su zero risultati con --org la CLI sonda il catalogo e mostra i nomi reali."""
    empty = {"total": {"value": 0, "relation": "eq"}, "num": 0, "start": 1, "results": []}
    probe = {
        "total": 25,
        "results": [
            {"_source": {"EnteResponsabile_s": "Citta' metropolitana di Bologna"}},
            {"_source": {"EnteResponsabile_s": "Regione Emilia-Romagna"}},
        ],
    }
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        side_effect=[httpx.Response(200, json=empty), httpx.Response(200, json=probe), httpx.Response(200, json=empty), httpx.Response(200, json=empty)]
    )
    result = runner.invoke(app, ["search", "--org", "comune di bologna", "--num", "2"])
    assert result.exit_code == 0, result.output
    assert "enti simili presenti in catalogo" in result.output
    assert "Citta' metropolitana di Bologna" in result.output


@respx.mock
def test_cli_search_org_zero_results_without_matches_suggests_territory():
    empty = {"total": {"value": 0, "relation": "eq"}, "num": 0, "start": 1, "results": []}
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        side_effect=[httpx.Response(200, json=empty), httpx.Response(200, json=empty), httpx.Response(200, json=empty), httpx.Response(200, json=empty)]
    )
    result = runner.invoke(app, ["search", "--org", "ente inesistente", "--num", "2"])
    assert result.exit_code == 0, result.output
    assert "AmbitoTerritoriale_s:Locale" in result.output


@respx.mock
def test_cli_search_compact_separates_updated_and_indexed(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["--format", "compact", "search", "--num", "2"])
    assert result.exit_code == 0, result.output
    first = json.loads(result.stdout.splitlines()[0])
    assert first["updated"] == "2025-02-11T00:00:00Z"
    assert first["indexed"] == "2026-04-25T15:37:01.891Z"


@respx.mock
def test_cli_search_table_explains_date_columns(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["--format", "table", "search", "--num", "2"], env={"COLUMNS": "300"})
    assert result.exit_code == 0, result.output
    assert "apiso_Modified_dt" in result.output


@respx.mock
def test_cli_search_json_notes_raw_date_field_with_date_filters(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(
        app, ["--format", "json", "search", "--updated-from", "2024-01-01", "--num", "2"]
    )
    assert result.exit_code == 0, result.output
    assert "Nota sulle date" in result.output
    # senza filtri data la nota non compare
    plain = runner.invoke(app, ["--format", "json", "search", "--num", "2"])
    assert "Nota sulle date" not in plain.output


@respx.mock
def test_cli_footprints_org_filter(search_response_json):
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["footprints", "--org", "agenzia delle entrate", "--num", "2"])
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.url.params["q"] == 'EnteResponsabile_s:/.*[aA][gG][eE][nN][zZ][iI][aA] [dD][eE][lL][lL][eE] [eE][nN][tT][rR][aA][tT][eE].*/'
    geojson = json.loads(result.stdout)
    assert "indexed" in geojson["features"][0]["properties"]


@respx.mock
def test_cli_search_org_zero_results_when_org_exists_blames_other_filters():
    """Se l'ente c'è in catalogo, lo zero viene da un altro filtro: dirlo."""
    empty = {"total": {"value": 0, "relation": "eq"}, "num": 0, "start": 1, "results": []}
    probe = {"total": 7131, "results": [{"_source": {"EnteResponsabile_s": "Regione Siciliana"}}]}
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        side_effect=[httpx.Response(200, json=empty), httpx.Response(200, json=probe)]
    )
    result = runner.invoke(
        app, ["search", "--org", "regione siciliana", "--data-category", "inlandWaters"]
    )
    assert result.exit_code == 0, result.output
    assert "esiste in catalogo" in result.output
    assert "rimuovi --data-category" in result.output


@respx.mock
def test_cli_search_org_acronym_suggests_full_responsible_name():
    """Una sigla sta nel contatto, non nell'ente responsabile: zero, ma il nome per esteso è proposto (#23)."""
    empty = {"total": {"value": 0, "relation": "eq"}, "num": 0, "start": 1, "results": []}
    full = "Agenzia Regionale per la Prevenzione, l'Ambiente e l'Energia dell'Emilia Romagna"
    probe = {
        "total": 394,
        "results": [{"_source": {"EnteResponsabile_s": full, "apiso_OrganizationName_txt": "ARPAE"}}],
    }
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        side_effect=[
            httpx.Response(200, json=empty),
            httpx.Response(200, json=probe),
            httpx.Response(200, json=empty),
            httpx.Response(200, json={"total": 394, "results": []}),
        ]
    )
    result = runner.invoke(app, ["search", "--org", "arpae"])
    assert result.exit_code == 0, result.output
    assert f"enti simili presenti in catalogo: {full}" in result.output


@respx.mock
def test_cli_search_org_contact_only_points_to_contact_query():
    """CSI compila i metadati per la Regione: non è mai ente responsabile, ma è fra i contatti."""
    empty = {"total": {"value": 0, "relation": "eq"}, "num": 0, "start": 1, "results": []}
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        side_effect=[
            httpx.Response(200, json=empty),
            httpx.Response(200, json=empty),
            httpx.Response(200, json={"total": 272, "results": []}),
        ]
    )
    result = runner.invoke(app, ["search", "--org", "csi"])
    assert result.exit_code == 0, result.output
    assert "compare in 272 schede fra gli enti citati nel metadato" in result.output
    assert "openrndt search --q 'apiso_OrganizationName_txt:\"csi\"'" in result.output
    assert "nessun ente in catalogo somiglia" not in result.output
    assert route.calls[2].request.url.params["q"] == '(apiso_OrganizationName_txt:"csi")'


@respx.mock
def test_cli_search_org_no_contact_hint_when_another_filter_gives_zero():
    """Se --org da solo trova record, lo zero viene da un altro filtro: niente avviso sui contatti."""
    empty = {"total": {"value": 0, "relation": "eq"}, "num": 0, "start": 1, "results": []}
    probe = {"total": 5, "results": [{"_source": {"EnteResponsabile_s": "Regione Piemonte"}}]}
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        side_effect=[
            httpx.Response(200, json=empty),
            httpx.Response(200, json=probe),
            httpx.Response(200, json={"total": 613, "results": []}),
        ]
    )
    result = runner.invoke(app, ["search", "--org", "piemonte", "--bbox", "7,44,8,45"])
    assert result.exit_code == 0, result.output
    assert "fra gli enti citati nel metadato" not in result.output
    assert route.call_count == 3


@respx.mock
def test_cli_search_org_probe_escapes_token():
    """La probe cerca il token come frase sul campo del contatto, quotato (#23)."""
    empty = {"total": {"value": 0, "relation": "eq"}, "num": 0, "start": 1, "results": []}
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        side_effect=[httpx.Response(200, json=empty), httpx.Response(200, json=empty), httpx.Response(200, json=empty), httpx.Response(200, json=empty)]
    )
    result = runner.invoke(app, ["search", "--org", "regione emilia-romagna"])
    assert result.exit_code == 0, result.output
    assert route.calls[1].request.url.params["q"] == '(apiso_OrganizationName_txt:"emilia-romagna")'


@respx.mock
def test_cli_search_json_notes_dates_when_sorting_by_index(search_response_json):
    """Anche `sys_modified_dt` è un campo data: la nota deve scattare."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(
        app, ["--format", "json", "search", "--sort", "sys_modified_dt:desc", "--num", "2"]
    )
    assert result.exit_code == 0, result.output
    assert "Nota sulle date" in result.output
    plain = runner.invoke(app, ["--format", "json", "search", "--sort", "title:asc", "--num", "2"])
    assert "Nota sulle date" not in plain.output


def test_record_dates_ignores_non_string_values():
    from openrndt.search import record_dates

    result = {"updated": 1234567890, "_source": {"apiso_Modified_dt": {"x": 1}}}
    assert record_dates(result) == (None, None)


def test_cli_search_rejects_malformed_bbox_without_network():
    """Nessuna route respx registrata: se partisse una richiesta, il test fallirebbe."""
    result = runner.invoke(app, ["search", "--bbox", "non,valido"])
    assert result.exit_code == 2
    assert "quattro valori" in result.output


def test_cli_footprints_rejects_malformed_bbox_without_network():
    result = runner.invoke(app, ["footprints", "--bbox", "12,45,11,44"])
    assert result.exit_code == 2
    assert "xmin" in result.output


@respx.mock
def test_cli_search_table_hides_url_and_renders_open(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["--format", "table", "search", "--num", "2"], env={"COLUMNS": "400"})
    assert result.exit_code == 0, result.output
    assert "open" in result.output
    assert "license" in result.output
    # il permalink resta fuori dalla tabella: intestazione e valori
    assert "url" not in result.output.split("\n")[2]
    assert "geoportal-catalog" not in result.output


@respx.mock
def test_cli_search_csv_keeps_url(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["--format", "csv", "search", "--num", "2"])
    assert result.exit_code == 0, result.output
    assert "url" in result.output.split("\n")[0]
    assert "geoportal-catalog" in result.output


@respx.mock
def test_cli_footprints_properties_carry_license_and_url(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["footprints", "--num", "2"])
    assert result.exit_code == 0, result.output
    props = json.loads(result.stdout)["features"][0]["properties"]
    assert "open" in props and "license" in props and "url" in props


@respx.mock
def test_cli_search_table_truncates_long_license(search_response_json):
    """Il campo del RNDT contiene spesso paragrafi interi: in tabella vanno tagliati."""
    payload = json.loads(json.dumps(search_response_json))
    lunga = "Dato concesso con licenza CC-BY-4.0 " + "con obbligo di citazione della fonte " * 5
    payload["results"][0]["_source"]["isOpendata"] = ["opendata", lunga]
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(return_value=httpx.Response(200, json=payload))
    result = runner.invoke(app, ["--format", "table", "search", "--num", "1"], env={"COLUMNS": "400"})
    assert result.exit_code == 0, result.output
    assert "…" in result.output
    assert lunga not in result.output.replace("\n", "")


@respx.mock
def test_cli_get_json_normalized(item_response_json):
    """`get` restituisce il documento normalizzato, con busta preservata."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA").mock(
        return_value=httpx.Response(200, json=item_response_json)
    )
    result = runner.invoke(app, ["--format", "json", "get", "age:D_E973_MARSAGLIA"])
    assert result.exit_code == 0, result.output
    doc = json.loads(result.stdout)
    assert doc["id"] == "age:D_E973_MARSAGLIA"
    assert doc["org"] == "Agenzia delle Entrate"
    assert doc["contact"]["email"] == "assistenzaweb@agenziaentrate.it"
    assert doc["bbox"]["xmin"] == 7.9496964
    assert doc["resources"]
    assert doc["_source"]["fileid"] == "age:D_E973_MARSAGLIA"


@respx.mock
def test_cli_get_raw_keeps_es_envelope(item_response_json):
    """`--raw` ripristina la busta Elasticsearch com'era ante 3.3.0."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA").mock(
        return_value=httpx.Response(200, json=item_response_json)
    )
    result = runner.invoke(app, ["--format", "json", "get", "age:D_E973_MARSAGLIA", "--raw"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == item_response_json


def _plain(text: str) -> str:
    """Testo senza codici ANSI, senza bordi del riquadro e su una riga sola.

    Rich colora le opzioni e manda a capo dentro il riquadro d'errore: cercare
    una stringa nell'output grezzo passa in locale e fallisce in CI, dove il
    colore è attivo e spezza `--raw` in mezzo ai codici di escape.
    """
    without_ansi = re.sub(r"\x1b\[[0-9;]*m", "", text)
    return " ".join(without_ansi.translate(str.maketrans("", "", "│╭╮╰╯─")).split())


def test_cli_get_raw_rejects_xml_and_html():
    """`--raw` riguarda solo il JSON: con --xml o --html è un errore, non un'opzione ignorata."""
    for flag in ("--xml", "--html"):
        result = runner.invoke(app, ["get", "age:D_E973_MARSAGLIA", "--raw", flag])
        assert result.exit_code == 2, result.output
        assert "riguarda solo l'output JSON" in _plain(result.output)


def test_public_api_exports_item_helpers():
    """Gli helper del documento normalizzato sono importabili dal package, non solo dal modulo."""
    import openrndt

    for name in ("item_record", "contact_point", "download_urls", "bbox_from_envelope", "resolve_item_id"):
        assert name in openrndt.__all__
        assert callable(getattr(openrndt, name))

_UUID = "7832b30d-8e4a-4900-836d-1d4e960c3325"


@respx.mock
def test_cli_get_resolves_bare_uuid():
    """`get <uuid-nudo>`: risoluzione via ricerca, poi scheda dell'ID completo."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"results": [{"id": f"r_sicili:{_UUID}"}]})
    )
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/r_sicili%3A{_UUID}").mock(
        return_value=httpx.Response(
            200,
            json={"_id": f"r_sicili:{_UUID}", "found": True, "_source": {"title": "PAI Regione Siciliana"}},
        )
    )
    result = runner.invoke(app, ["--format", "json", "get", _UUID])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["id"] == f"r_sicili:{_UUID}"


@respx.mock
def test_cli_get_bare_uuid_not_found_shows_message():
    """`get <uuid-nudo>` senza corrispondenze: exit 1 e messaggio leggibile."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    result = runner.invoke(app, ["get", _UUID])
    assert result.exit_code == 1
    assert "non trovato" in result.output.lower()


@respx.mock
def test_cli_search_id_bare_uuid_resolved_before_search():
    """`search --id <uuid-nudo>`: risolto nell'ID completo prima della chiamata filtrata."""
    search_route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"results": [{"id": f"r_sicili:{_UUID}"}], "total": 1})
    )
    result = runner.invoke(app, ["--format", "json", "search", "--id", _UUID, "--num", "1"])
    assert result.exit_code == 0, result.output
    params = search_route.calls.last.request.url.params
    assert params["id"] == f"r_sicili:{_UUID}"
    assert search_route.calls[0].request.url.params["q"] == _UUID


# --- geolibre_url (issue #24) ------------------------------------------------


@respx.mock
def test_cli_geolibre_url_in_json_csv_footprints_not_table(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    expected = "https://web.geolibre.app/?plugin=openrndt-geolibre&rndt=age%3AD_E973_MARSAGLIA"

    out = runner.invoke(app, ["--format", "json", "search", "--num", "2"])
    assert json.loads(out.stdout)["results"][0]["geolibre_url"] == expected

    out = runner.invoke(app, ["--format", "csv", "search", "--num", "2"])
    assert out.stdout.splitlines()[0].split(",").count("geolibre_url") == 1
    assert expected in out.stdout

    out = runner.invoke(app, ["footprints", "--num", "2"])
    assert json.loads(out.stdout)["features"][0]["properties"]["geolibre_url"] == expected

    out = runner.invoke(app, ["--format", "table", "search", "--num", "2"], env={"COLUMNS": "400"})
    assert out.exit_code == 0, out.output
    assert "geolibre" not in out.stdout


# --- org dall'ente responsabile negli output della CLI (#23) -----------------

PIEMONTE_CSI = {
    "total": 1,
    "results": [
        {
            "id": "r_piemon:x",
            "title": "PRAE",
            "bbox": {"xmin": 7.0, "ymin": 44.0, "xmax": 8.0, "ymax": 45.0},
            "_source": {"EnteResponsabile_s": "Regione Piemonte", "apiso_OrganizationName_txt": "CSI Piemonte"},
        }
    ],
}


@respx.mock
def test_cli_csv_org_is_responsible_party():
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=PIEMONTE_CSI)
    )
    result = runner.invoke(app, ["--format", "csv", "search", "--org", "regione piemonte"])
    assert result.exit_code == 0, result.output
    assert "Regione Piemonte" in result.stdout
    assert "CSI Piemonte" not in result.stdout


@respx.mock
def test_cli_footprints_org_is_responsible_party():
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=PIEMONTE_CSI)
    )
    result = runner.invoke(app, ["footprints", "--org", "regione piemonte"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["features"][0]["properties"]["org"] == "Regione Piemonte"


@respx.mock
def test_cli_search_org_suggestions_skip_records_without_responsible_party():
    """Un nome preso dal contatto non si trova con --org: non va suggerito."""
    empty = {"total": {"value": 0, "relation": "eq"}, "num": 0, "start": 1, "results": []}
    probe = {
        "total": 2,
        "results": [
            {"_source": {"apiso_OrganizationName_txt": "ISPRA Ufficio X"}},
            {"_source": {"EnteResponsabile_s": "Istituto Superiore per la Protezione e la Ricerca Ambientale"}},
        ],
    }
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        side_effect=[httpx.Response(200, json=empty), httpx.Response(200, json=probe), httpx.Response(200, json=empty), httpx.Response(200, json=empty)]
    )
    result = runner.invoke(app, ["search", "--org", "ispra ufficio"])
    assert result.exit_code == 0, result.output
    assert "Istituto Superiore per la Protezione e la Ricerca Ambientale" in result.output
    assert "ISPRA Ufficio X" not in result.output


@respx.mock
def test_cli_search_org_contact_hint_keeps_base_url():
    """Il comando suggerito interroga lo stesso catalogo su cui è stato contato."""
    other = "https://example.org/RNDT"
    empty = {"total": {"value": 0, "relation": "eq"}, "num": 0, "start": 1, "results": []}
    respx.get(f"{other}/rest/metadata/search").mock(
        side_effect=[httpx.Response(200, json=empty), httpx.Response(200, json=empty), httpx.Response(200, json={"total": 5, "results": []})]
    )
    result = runner.invoke(app, ["--base-url", other, "search", "--org", "csi"])
    assert result.exit_code == 0, result.output
    assert f"openrndt --base-url {other} search --q" in result.output


# --- link GeoLibre per la ricerca intera (issue #27) -------------------------


@respx.mock
def test_cli_search_json_has_geolibre_search_after_total(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["--format", "json", "search", "--q", "fiumi", "--time", "2020-01-01/2021-01-01"])
    assert result.exit_code == 0, result.output
    out = json.loads(result.stdout)
    assert list(out)[:2] == ["total", "geolibre_search"]
    link = out["geolibre_search"]
    # Senza --bbox la mappa si apre sul riquadro dei risultati della pagina.
    assert link["url"].startswith("https://web.geolibre.app/?plugin=openrndt-geolibre&rndt=fiumi&rndtView=")
    assert link["untranslated"] == ["time"]


@respx.mock
def test_cli_search_geolibre_link_prints_only_url(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(
        app,
        ["--format", "table", "search", "--q", "fiumi", "--bbox", "9,45,10,46", "--sort", "relevance", "--geolibre-link"],
    )
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "https://web.geolibre.app/?plugin=openrndt-geolibre&rndt=fiumi&rndtBbox=9,45,10,46"
    assert "Non applicati nel link (il plugin non li ha): --sort" in result.stderr


@respx.mock
def test_cli_search_geolibre_link_notes_comma_in_org(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = runner.invoke(app, ["search", "--org", "Agenzia per la Prevenzione, l'Ambiente", "--geolibre-link"])
    assert result.exit_code == 0, result.output
    assert "rndtOrg=Agenzia%20per%20la%20Prevenzione,%20l%27Ambiente" in result.stdout
    assert "Nota sul link: org: il plugin legge la virgola" in result.stderr
