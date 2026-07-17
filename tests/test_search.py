"""Test del modulo search con HTTP mockato via respx."""

from __future__ import annotations

import httpx
import pytest
import respx

from openrndt.config import DEFAULT_BASE_URL
from openrndt.search import MAX_NUM, compact_results, search


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
    assert set(first) == {"id", "title", "org", "type", "category", "updated", "resources"}


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
