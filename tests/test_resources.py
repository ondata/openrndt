"""Test del modulo resources (estrazione + check endpoint)."""

from __future__ import annotations

import httpx
import respx

from openrndt.resources import check_resources, extract_resources


def test_extract_resources_dedup_and_filter_non_resource_links(item_response_json):
    rows = extract_resources(item_response_json)
    assert rows == [
        {
            "type": "WMS",
            "url": "https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities",
            "source": "links_s",
        },
        {
            "type": "WFS",
            "url": "https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php?SERVICE=WFS&REQUEST=GetCapabilities&VERSION=2.0.0",
            "source": "links_s",
        },
    ]


def test_extract_resources_infers_from_links_when_dctype_missing():
    payload = {
        "_source": {},
        "links": [
            {"rel": "related", "href": "https://example.test/geoserver/wms?service=WMS&request=GetCapabilities"},
            {"rel": "enclosure", "href": "https://example.test/export.zip"},
            {"rel": "alternate", "href": "https://example.test/item/123"},
        ],
    }
    rows = extract_resources(payload)
    assert rows == [
        {
            "type": "WMS",
            "url": "https://example.test/geoserver/wms?service=WMS&request=GetCapabilities",
            "source": "links",
        },
        {
            "type": "download",
            "url": "https://example.test/export.zip",
            "source": "links",
        },
    ]


@respx.mock
def test_check_resources_adds_http_status():
    respx.head("https://ok.test/wms?service=WMS").mock(return_value=httpx.Response(200))
    respx.head("https://bad.test/wfs?service=WFS").mock(return_value=httpx.Response(503))
    rows = [
        {"type": "WMS", "url": "https://ok.test/wms?service=WMS", "source": "links_s"},
        {"type": "WFS", "url": "https://bad.test/wfs?service=WFS", "source": "links_s"},
    ]
    checked = check_resources(rows, timeout=1)
    assert checked[0]["status_code"] == 200
    assert checked[0]["ok"] is True
    assert checked[0]["method"] == "HEAD"
    assert checked[1]["status_code"] == 503
    assert checked[1]["ok"] is False
    assert checked[1]["method"] == "HEAD"


@respx.mock
def test_check_resources_handles_network_errors():
    respx.head("https://down.test/wms?service=WMS").mock(side_effect=httpx.ConnectError("down"))
    checked = check_resources(
        [{"type": "WMS", "url": "https://down.test/wms?service=WMS", "source": "links_s"}],
        timeout=1,
    )
    assert checked[0]["ok"] is False
    assert checked[0]["status_code"] is None
    assert checked[0]["error"] == "ConnectError"


@respx.mock
def test_check_resources_falls_back_to_streaming_get_when_head_not_allowed():
    respx.head("https://fallback.test/data.zip").mock(return_value=httpx.Response(405))
    respx.get("https://fallback.test/data.zip").mock(return_value=httpx.Response(200))
    checked = check_resources(
        [{"type": "download", "url": "https://fallback.test/data.zip", "source": "links_s"}],
        timeout=1,
    )
    assert checked[0]["status_code"] == 200
    assert checked[0]["ok"] is True
    assert checked[0]["method"] == "GET"
