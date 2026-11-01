"""Test del modulo item (dettaglio metadato)."""

from __future__ import annotations

import httpx
import pytest
import respx

from openrndt.config import DEFAULT_BASE_URL
from openrndt.item import (
    AmbiguousItemIdError,
    ItemNotFoundError,
    get_item,
    get_item_html,
    get_item_xml,
    resolve_item_id,
)


@respx.mock
def test_get_item_json(item_response_json):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA").mock(
        return_value=httpx.Response(200, json=item_response_json)
    )
    payload = get_item("age:D_E973_MARSAGLIA")
    assert payload["_id"] == "age:D_E973_MARSAGLIA"
    assert payload["_source"]["title"].startswith("Cartografia catastale")


@respx.mock
def test_get_item_xml_returns_iso19139(item_response_xml):
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA/xml").mock(
        return_value=httpx.Response(200, text=item_response_xml, headers={"content-type": "application/xml"})
    )
    xml = get_item_xml("age:D_E973_MARSAGLIA")
    assert xml.startswith("<?xml")
    assert "gmd:MD_Metadata" in xml


@respx.mock
def test_get_item_html():
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/abc%3A123/html").mock(
        return_value=httpx.Response(200, text="<html><body>ok</body></html>")
    )
    assert "<html>" in get_item_html("abc:123")


@respx.mock
def test_get_item_not_found_raises():
    """L'API torna 200 con found:false per ID inesistenti — deve sollevare ItemNotFoundError."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/inesistente").mock(
        return_value=httpx.Response(200, json={"_id": "inesistente", "found": False})
    )
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    with pytest.raises(ItemNotFoundError):
        get_item("inesistente")


_AGEA_FILEID = "agea:OI:ORTOIMMAGINI:m004"
_AGEA_ID = "agea:OI:DATEVOLO:m001+-++-+2026-09-25+12:42:55"


@respx.mock
def test_get_item_falls_back_from_fileid_to_catalog_id():
    """Un fileid che non è l'`_id` del catalogo (schede AGEA): si risale all'`_id` con `fileid:"…"`."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/agea%3AOI%3AORTOIMMAGINI%3Am004").mock(
        return_value=httpx.Response(200, json={"_id": _AGEA_FILEID, "found": False})
    )
    search_route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"results": [{"id": _AGEA_ID}]})
    )
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/agea%3AOI%3ADATEVOLO%3Am001%2B-%2B%2B-%2B2026-09-25%2B12%3A42%3A55").mock(
        return_value=httpx.Response(200, json={"_id": _AGEA_ID, "found": True, "_source": {"fileid": _AGEA_FILEID}})
    )
    payload = get_item(_AGEA_FILEID)
    assert payload["_id"] == _AGEA_ID
    assert search_route.calls.last.request.url.params["q"] == f'fileid:"{_AGEA_FILEID}"'


@respx.mock
def test_get_item_fileid_ambiguous():
    """Lo stesso fileid su più schede: AmbiguousItemIdError con gli `_id`."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/dup").mock(
        return_value=httpx.Response(200, json={"_id": "dup", "found": False})
    )
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"results": [{"id": "a:1"}, {"id": "a:2"}]})
    )
    with pytest.raises(AmbiguousItemIdError) as exc:
        get_item("dup")
    assert exc.value.candidates == ["a:1", "a:2"]

_UUID = "7832b30d-8e4a-4900-836d-1d4e960c3325"


@respx.mock
def test_get_item_resolves_bare_uuid():
    """Un UUID nudo si risolve via ricerca, tenendo l'unico risultato che lo contiene nell'ID."""
    search_route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"id": "cmto:3aff0e39-b60f-4900-bff8-1931f1278a5f"},
                    {"id": f"r_sicili:{_UUID}"},
                ]
            },
        )
    )
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/r_sicili%3A{_UUID}").mock(
        return_value=httpx.Response(200, json={"_id": f"r_sicili:{_UUID}", "found": True, "_source": {}})
    )
    payload = get_item(_UUID)
    assert payload["_id"] == f"r_sicili:{_UUID}"
    assert search_route.calls.last.request.url.params["q"] == _UUID


@respx.mock
def test_get_item_bare_uuid_not_found():
    """UUID nudo senza corrispondenze: ItemNotFoundError."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"results": [{"id": "age:altro-metadato"}]})
    )
    with pytest.raises(ItemNotFoundError):
        get_item(_UUID)


@respx.mock
def test_get_item_bare_uuid_ambiguous():
    """Lo stesso UUID in più namespace: AmbiguousItemIdError."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"id": f"r_sicili:{_UUID}"}, {"id": f"age:{_UUID}"}]},
        )
    )
    with pytest.raises(AmbiguousItemIdError):
        get_item(_UUID)


@respx.mock
def test_resolve_item_id_case_insensitive():
    """UUID in maiuscolo: regex e confronto insensitive, hit sull'ID minuscolo."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"results": [{"id": f"r_sicili:{_UUID}"}]})
    )
    assert resolve_item_id(_UUID.upper()) == f"r_sicili:{_UUID}"


@respx.mock
def test_resolve_item_id_passthrough_without_search(item_response_json):
    """ID già namespaced: nessuna ricerca, richiesta item diretta."""
    search_route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/age%3AD_E973_MARSAGLIA").mock(
        return_value=httpx.Response(200, json=item_response_json)
    )
    assert resolve_item_id("age:D_E973_MARSAGLIA") == "age:D_E973_MARSAGLIA"
    assert search_route.call_count == 0



@respx.mock
@pytest.mark.parametrize("suffix", ["xml", "html"])
def test_get_item_xml_html_fall_back_from_fileid(suffix):
    """`--xml`/`--html` con un fileid: il server risponde 500/501, si risale all'`_id` e si riprova."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/item/agea%3AOI%3AORTOIMMAGINI%3Am004/{suffix}").mock(
        return_value=httpx.Response(500)
    )
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(
        return_value=httpx.Response(200, json={"results": [{"id": _AGEA_ID}]})
    )
    respx.get(
        f"{DEFAULT_BASE_URL}/rest/metadata/item/agea%3AOI%3ADATEVOLO%3Am001%2B-%2B%2B-%2B2026-09-25%2B12%3A42%3A55/{suffix}"
    ).mock(return_value=httpx.Response(200, text="<ok/>"))
    fetch = get_item_xml if suffix == "xml" else get_item_html
    assert fetch(_AGEA_FILEID) == "<ok/>"
