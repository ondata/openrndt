"""Test del modulo item (dettaglio metadato)."""

from __future__ import annotations

import httpx
import respx

from openrndt.config import DEFAULT_BASE_URL
from openrndt.item import get_item, get_item_html, get_item_xml


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
