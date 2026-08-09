"""Test del modulo resources (estrazione + check endpoint)."""

from __future__ import annotations

import socket

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


def test_extract_resources_normalizes_kind_and_skips_generic_link():
    payload = {
        "_source": {"links_s": ["https://example.test/landing"]},
        "links": [
            {"rel": "related", "dctype": "download", "href": "https://example.test/data.gpkg"},
            {"rel": "related", "dctype": "LINK", "href": "https://example.test/page"},
        ],
    }
    rows = extract_resources(payload)
    assert rows == [{"type": "download", "url": "https://example.test/data.gpkg", "source": "links"}]


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
    assert checked[0]["error"] is None
    assert checked[0]["redirect_url"] is None
    assert checked[1]["status_code"] == 503
    assert checked[1]["ok"] is False
    assert checked[1]["method"] == "HEAD"
    assert checked[1]["error"] is None
    assert checked[1]["redirect_url"] is None


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
    assert checked[0]["method"] == "HEAD"


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
    assert checked[0]["error"] is None
    assert checked[0]["redirect_url"] is None


def test_check_resources_blocks_private_hosts():
    checked = check_resources(
        [{"type": "download", "url": "http://127.0.0.1:8080/data.zip", "source": "links_s"}],
        timeout=1,
    )
    assert checked[0]["ok"] is False
    assert checked[0]["status_code"] is None
    assert checked[0]["error"] == "url-blocked:loopback-not-allowed"
    assert checked[0]["method"] == "HEAD"


def test_check_resources_blocks_dns_resolving_to_private_ip(monkeypatch):
    def _fake_getaddrinfo(host: str, port: object, proto: int):  # type: ignore[no-untyped-def]
        assert host == "evil.test"
        assert proto == socket.IPPROTO_TCP
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    checked = check_resources(
        [{"type": "WMS", "url": "https://evil.test/service", "source": "links_s"}],
        timeout=1,
    )
    assert checked[0]["ok"] is False
    assert checked[0]["status_code"] is None
    assert checked[0]["error"] == "url-blocked:dns-resolves-to-loopback-not-allowed"


@respx.mock
def test_check_resources_allows_dns_resolving_to_public_ip(monkeypatch):
    def _fake_getaddrinfo(host: str, port: object, proto: int):  # type: ignore[no-untyped-def]
        assert host == "public.test"
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    respx.head("https://public.test/service").mock(return_value=httpx.Response(200))
    checked = check_resources(
        [{"type": "WMS", "url": "https://public.test/service", "source": "links_s"}],
        timeout=1,
    )
    assert checked[0]["ok"] is True
    assert checked[0]["status_code"] == 200
    assert checked[0]["error"] is None


@respx.mock
def test_check_resources_does_not_follow_redirects():
    respx.head("https://redir.test/service").mock(
        return_value=httpx.Response(302, headers={"Location": "http://169.254.1.10/internal"})
    )
    checked = check_resources(
        [{"type": "WMS", "url": "https://redir.test/service", "source": "links_s"}],
        timeout=1,
    )
    assert checked[0]["status_code"] == 302
    # 3xx = destinazione non verificata (redirect non seguiti): ok deve restare False.
    assert checked[0]["ok"] is False
    assert checked[0]["redirect_url"] == "http://169.254.1.10/internal"
