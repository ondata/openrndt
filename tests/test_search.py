"""Test del modulo search con HTTP mockato via respx."""

from __future__ import annotations

import httpx
import pytest
import respx

from openrndt.config import DEFAULT_BASE_URL
from openrndt.search import (
    MAX_NUM,
    compact_results,
    organization_names,
    record_dates,
    search,
)


@respx.mock
def test_search_returns_dict_on_json(search_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json=search_response_json)
    )
    result = search(q="catasto", num=2)
    assert isinstance(result, dict)
    assert result["total"] == 23580
    assert len(result["results"]) == 2


@respx.mock
def test_search_passes_all_params():
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"total": 0, "results": []})
    )
    search(
        q="suolo",
        bbox="7,44,8,45",
        bbox_crs="EPSG:4326",
        data_category="planningCadastre",
        time="2024-01-01/2024-12-31",
        sort="title:desc",
        start=11,
        num=20,
        item_id="abc",
    )
    request = route.calls.last.request
    params = dict(request.url.params)
    assert params["q"] == "(suolo) AND keywords_s:planningCadastre"
    assert "dataCategory" not in params, "dataCategory non è un filtro nativo del RNDT"
    assert params["bbox"] == "7,44,8,45"
    assert params["time"] == "2024-01-01/2024-12-31"
    assert params["sort"] == "title:desc"
    assert params["start"] == "11"
    assert params["num"] == "20"
    assert params["id"] == "abc"
    assert params["f"] == "json"


@respx.mock
def test_data_category_alone_becomes_keywords_clause():
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"total": 0, "results": []})
    )
    search(data_category="planningCadastre", num=1)
    params = dict(route.calls.last.request.url.params)
    assert params["q"] == "keywords_s:planningCadastre"


@respx.mock
def test_data_category_multiple_becomes_or_clause():
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"total": 0, "results": []})
    )
    search(data_category="planningCadastre,boundaries", num=1)
    params = dict(route.calls.last.request.url.params)
    assert params["q"] == "keywords_s:(planningCadastre OR boundaries)"


@respx.mock
def test_search_returns_text_on_non_json_format():
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, text="title,id\nfoo,bar\n", headers={"content-type": "text/csv"})
    )
    result = search(num=1, fmt="csv")
    assert isinstance(result, str)
    assert "title,id" in result


@respx.mock
def test_search_passes_modified_param():
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"total": 0, "results": []})
    )
    search(modified="2024-01-01/2024-12-31", num=1)
    params = dict(route.calls.last.request.url.params)
    assert params["modified"] == "2024-01-01/2024-12-31"


@respx.mock
def test_search_builds_updated_and_published_lucene_clauses():
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"total": 0, "results": []})
    )
    search(
        q="catasto",
        updated_from="2024-01-01",
        updated_to="2024-12-31",
        published_from="2020-01-01",
        published_to="2020-12-31",
        num=1,
    )
    params = dict(route.calls.last.request.url.params)
    assert params["q"] == (
        "(catasto) AND apiso_Modified_dt:[2024-01-01T00:00:00Z TO 2024-12-31T23:59:59Z] "
        "AND apiso_PublicationDate_dt:[2020-01-01T00:00:00Z TO 2020-12-31T23:59:59Z]"
    )


def test_search_rejects_bbox_crs_without_bbox():
    with pytest.raises(ValueError, match="bbox_crs"):
        search(bbox_crs="EPSG:4326")


def test_search_rejects_unsupported_bbox_crs():
    with pytest.raises(ValueError, match="non supportato"):
        search(bbox="7,44,8,45", bbox_crs="EPSG:3857")


def test_search_rejects_modified_and_updated_range_together():
    with pytest.raises(ValueError, match="Usa `modified` oppure `updated_from/updated_to`"):
        search(modified="2024-01-01/2024-12-31", updated_from="2024-01-01")


def test_search_rejects_invalid_date_format():
    with pytest.raises(ValueError, match="yyyy-mm-dd"):
        search(updated_from="2024/01/01")


def test_search_rejects_invalid_calendar_date():
    with pytest.raises(ValueError, match="calendario valida"):
        search(updated_from="2024-13-40")


@respx.mock
def test_search_wraps_q_when_combined_with_other_clauses():
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"total": 0, "results": []})
    )
    search(q="title:catasto OR title:particelle", updated_from="2024-01-01", num=1)
    params = dict(route.calls.last.request.url.params)
    assert params["q"].startswith("(title:catasto OR title:particelle) AND ")


@respx.mock
def test_data_category_only_blank_values_ignored():
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"total": 0, "results": []})
    )
    search(data_category=" , ", num=1)
    params = dict(route.calls.last.request.url.params)
    assert "q" not in params


def test_search_validates_num_max():
    with pytest.raises(ValueError, match="non può superare"):
        search(num=MAX_NUM + 1)


def test_search_validates_start_positive():
    with pytest.raises(ValueError, match="≥ 1"):
        search(start=0)


def test_compact_results_extracts_high_signal_fields(search_response_json):
    records = compact_results(search_response_json)
    assert len(records) == 2
    first = records[0]
    assert first["id"] == "age:D_E973_MARSAGLIA"
    assert first["org"] == "Agenzia delle Entrate"  # da apiso_OrganizationName_txt
    assert first["type"] == "dataset"
    assert first["category"] == "planningCadastre"  # da apiso_TopicCategory_s
    assert first["resources"] == ["WFS", "WMS"]  # dedup + sort dai links
    assert set(first) == {"id", "title", "org", "type", "category", "updated", "indexed", "resources"}


def test_compact_results_resources_dedup_and_skip_metadata_links(search_response_json):
    second = compact_results(search_response_json)[1]
    # links: WFS, WFS, WMS + 3 alternate → solo i servizi, dedotti e ordinati
    assert second["resources"] == ["WFS", "WMS"]


def test_compact_results_empty_payload():
    assert compact_results({"results": []}) == []
    assert compact_results({}) == []


def test_compact_results_falls_back_to_author_name():
    payload = {"results": [{"id": "x", "title": "T", "author": {"name": "csw.foo"}}]}
    record = compact_results(payload)[0]
    assert record["org"] == "csw.foo"
    assert record["resources"] == []
    assert record["category"] is None


def test_compact_results_resources_includes_bare_enclosure_as_download():
    # rel=enclosure senza dctype: download diretto, non un servizio WMS/WFS.
    payload = {
        "results": [
            {
                "id": "x",
                "title": "T",
                "links": [{"rel": "enclosure", "url": "http://example/download.zip"}],
            }
        ]
    }
    assert compact_results(payload)[0]["resources"] == ["download"]


def test_compact_results_category_when_keywords_s_is_single_string():
    # keywords_s a volte è una stringa singola, non un array.
    payload = {
        "results": [
            {
                "id": "x",
                "title": "T",
                "_source": {"keywords_s": "planningCadastre"},
            }
        ]
    }
    assert compact_results(payload)[0]["category"] == "planningCadastre"


def test_compact_results_category_from_categories_when_keywords_unhelpful():
    # keywords_s popolato ma senza valori ISO: la categoria va cercata anche in `categories`
    payload = {
        "results": [
            {
                "id": "x",
                "title": "T",
                "categories": [{"term": "planningCadastre"}],
                "_source": {"keywords_s": ["suolo", "frane"]},
            }
        ]
    }
    assert compact_results(payload)[0]["category"] == "planningCadastre"


def test_compact_results_separates_record_and_index_dates(search_response_json):
    """`updated` è la data della scheda, `indexed` quella di indicizzazione.

    Il campo top-level `updated` dell'API è `sys_modified_dt`: l'istante in cui
    il catalogo ha reindicizzato il record. La data su cui filtrano
    `updated_from`/`updated_to` è invece `apiso_Modified_dt`.
    """
    first = compact_results(search_response_json)[0]
    assert first["updated"] == "2025-02-11T00:00:00Z"  # _source.apiso_Modified_dt
    assert first["indexed"] == "2026-04-25T15:37:01.891Z"  # top-level updated


def test_record_dates_falls_back_to_top_level_updated():
    result = {"updated": "2026-04-25T00:00:00Z", "_source": {}}
    assert record_dates(result) == (None, "2026-04-25T00:00:00Z")


@respx.mock
def test_search_org_uses_analyzed_field_phrase():
    """`org` cerca la frase sul campo analizzato: case-insensitive, niente wildcard."""
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"total": 0, "results": []})
    )
    search(org="comune di torino", num=1)
    assert route.calls.last.request.url.params["q"] == 'apiso_OrganizationName_txt:"comune di torino"'


@respx.mock
def test_search_org_exact_uses_keyword_field():
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"total": 0, "results": []})
    )
    search(org_exact="Comune di Torino", num=1)
    assert route.calls.last.request.url.params["q"] == 'EnteResponsabile_s:"Comune di Torino"'


@respx.mock
def test_search_org_combines_in_and_with_other_filters():
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"total": 0, "results": []})
    )
    search(q="ortofoto", org="comune di torino", data_category="imageryBaseMapsEarthCover", num=1)
    q = route.calls.last.request.url.params["q"]
    assert q == (
        '(ortofoto) AND apiso_OrganizationName_txt:"comune di torino" '
        "AND keywords_s:imageryBaseMapsEarthCover"
    )


def test_search_rejects_org_and_org_exact_together():
    with pytest.raises(ValueError, match="`org` oppure `org_exact`"):
        search(org="x", org_exact="y")


def test_search_rejects_empty_org():
    with pytest.raises(ValueError, match="`org` non può essere vuoto"):
        search(org="   ")


@respx.mock
def test_search_org_escapes_quotes():
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"total": 0, "results": []})
    )
    search(org='comune "x"', num=1)
    assert route.calls.last.request.url.params["q"] == 'apiso_OrganizationName_txt:"comune \\"x\\""'


def test_organization_names_ranks_by_frequency():
    payload = {
        "results": [
            {"_source": {"EnteResponsabile_s": "Regione Emilia-Romagna"}},
            {"_source": {"EnteResponsabile_s": "Citta' metropolitana di Bologna"}},
            {"_source": {"EnteResponsabile_s": "Regione Emilia-Romagna"}},
            {"_source": {"apiso_OrganizationName_txt": "ARPAE"}},
            {"_source": {}},
        ]
    }
    assert organization_names(payload) == [
        "Regione Emilia-Romagna",
        "ARPAE",
        "Citta' metropolitana di Bologna",
    ]
