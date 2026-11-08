"""Temi e cluster INSPIRE: albero offline e filtro su tutte le forme."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from typer.testing import CliRunner

from openrndt import inspire_tree, search
from openrndt.cli import app
from openrndt.codelists import INSPIRE_CLUSTERS, INSPIRE_THEMES, INSPIRE_VARIANTS
from openrndt.config import DEFAULT_BASE_URL
from openrndt.search import geolibre_search_url

runner = CliRunner()
SEARCH_URL = f"{DEFAULT_BASE_URL}/rest/metadata/search"
HY = 'INSPIRETheme_s:("Idrografia" OR "Hydrography" OR "hy" OR "idrografia")'


def _route():
    return respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"total": 0, "results": []}))


def test_every_theme_is_in_exactly_one_cluster():
    assert len(INSPIRE_THEMES) == 34
    assert len(INSPIRE_CLUSTERS) == 9
    codes = [code for cluster in INSPIRE_CLUSTERS.values() for code in cluster["temi"]]
    assert sorted(codes) == sorted(INSPIRE_THEMES)
    assert set(INSPIRE_VARIANTS) <= set(INSPIRE_THEMES)


def test_inspire_tree_shape():
    tree = inspire_tree()
    assert len(tree) == 9
    mare = next(c for c in tree if c["cluster"] == "mare-atmosfera")
    assert {"codice": "sr", "it": "Regioni marine", "en": "Sea regions"} in mare["temi"]


@respx.mock
@pytest.mark.parametrize("value", ["hy", "HY", "Idrografia", "hydrography", " hy , idrografia "])
def test_theme_by_code_or_name_expands_to_all_forms(value):
    route = _route()
    search(inspire_theme=value, num=1)
    assert dict(route.calls.last.request.url.params)["q"] == HY


@respx.mock
def test_several_themes_are_in_or():
    route = _route()
    search(inspire_theme="hy,oi", num=1)
    q = dict(route.calls.last.request.url.params)["q"]
    assert q.count("INSPIRETheme_s:") == 1
    assert '"Hydrography"' in q
    assert '"Ortoimmagini"' in q


@respx.mock
def test_cluster_expands_to_its_themes():
    route = _route()
    search(inspire_cluster="monitoraggio", num=1)
    assert dict(route.calls.last.request.url.params)["q"] == (
        'INSPIRETheme_s:("Impianti di monitoraggio ambientale" OR "Environmental monitoring facilities" OR "ef")'
    )


@respx.mock
def test_theme_combines_in_and_with_other_filters():
    route = _route()
    search(q="fiumi", inspire_theme="hy", inspire_cluster="monitoraggio", num=1)
    q = dict(route.calls.last.request.url.params)["q"]
    assert q.startswith("(fiumi) AND ")
    assert f" AND {HY} AND " in q


@respx.mock
def test_blank_values_add_no_clause():
    route = _route()
    search(inspire_theme=" , ", inspire_cluster=" ", num=1)
    assert "q" not in dict(route.calls.last.request.url.params)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [({"inspire_theme": "EU"}, "Tema INSPIRE sconosciuto: EU"), ({"inspire_cluster": "boh"}, "Cluster INSPIRE sconosciuto: boh")],
)
def test_unknown_values_raise(kwargs, message):
    with pytest.raises(ValueError, match=message):
        search(num=1, **kwargs)


def test_geolibre_link():
    one = geolibre_search_url(inspire_theme="Idrografia")
    assert one["url"].endswith("&rndtTheme=hy")
    assert one["untranslated"] == []
    assert one["notes"] == []
    assert geolibre_search_url(inspire_theme="hy,oi")["untranslated"] == ["inspire_theme"]
    assert geolibre_search_url(inspire_cluster="statistica")["untranslated"] == ["inspire_cluster"]


@respx.mock
def test_cli_search_option():
    route = _route()
    result = runner.invoke(app, ["--format", "json", "search", "--inspire-theme", "hy"])
    assert result.exit_code == 0, result.output
    assert dict(route.calls.last.request.url.params)["q"] == HY
    assert "tema INSPIRE" in result.stderr


@respx.mock
def test_cli_footprints_option():
    route = _route()
    result = runner.invoke(app, ["footprints", "--inspire-cluster", "monitoraggio"])
    assert result.exit_code == 0, result.output
    assert '"ef"' in dict(route.calls.last.request.url.params)["q"]


def test_cli_unknown_theme_exits_2():
    result = runner.invoke(app, ["search", "--inspire-theme", "EU"])
    assert result.exit_code == 2
    assert "discover --what inspire_themes" in result.output


@respx.mock(assert_all_called=False)
def test_discover_tree_json_offline():
    result = runner.invoke(app, ["--format", "json", "discover", "--what", "inspire_themes"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == inspire_tree()


@respx.mock(assert_all_called=False)
def test_discover_tree_csv_one_row_per_theme():
    result = runner.invoke(app, ["--format", "csv", "discover", "--what", "inspire_themes"])
    assert result.exit_code == 0, result.output
    assert len(result.stdout.strip().splitlines()) == 35
    assert "scienze-terra" in result.stdout
