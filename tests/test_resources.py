"""Test del modulo resources (estrazione + check endpoint)."""

from __future__ import annotations

import socket

import httpx
import respx

from openrndt import resources as resources_module
from openrndt.resources import _MAX_REDIRECTS, check_resources, extract_resources


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
    respx.get("https://bad.test/wfs?service=WFS").mock(return_value=httpx.Response(503))
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
    # HEAD fallito -> riprova in GET, che conferma il 503.
    assert checked[1]["method"] == "GET"
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
def test_check_resources_falls_back_to_get_when_head_is_rejected():
    # WMS/WFS reali rispondono 403/500 a HEAD ma 200 a GET: senza fallback
    # il comando dichiarerebbe rotti endpoint funzionanti.
    respx.head("https://wms.test/ows").mock(return_value=httpx.Response(500))
    respx.get("https://wms.test/ows").mock(return_value=httpx.Response(200))
    respx.head("https://wfs.test/ows").mock(return_value=httpx.Response(403))
    respx.get("https://wfs.test/ows").mock(return_value=httpx.Response(200))
    checked = check_resources(
        [
            {"type": "WMS", "url": "https://wms.test/ows", "source": "links_s"},
            {"type": "WFS", "url": "https://wfs.test/ows", "source": "links_s"},
        ],
        timeout=1,
    )
    assert [r["ok"] for r in checked] == [True, True]
    assert [r["status_code"] for r in checked] == [200, 200]
    assert [r["method"] for r in checked] == ["GET", "GET"]


@respx.mock
def test_check_resources_keeps_get_status_when_endpoint_is_really_down():
    respx.head("https://gone.test/ows").mock(return_value=httpx.Response(404))
    respx.get("https://gone.test/ows").mock(return_value=httpx.Response(404))
    checked = check_resources(
        [{"type": "WMS", "url": "https://gone.test/ows", "source": "links_s"}],
        timeout=1,
    )
    assert checked[0]["ok"] is False
    assert checked[0]["status_code"] == 404
    assert checked[0]["method"] == "GET"


def test_check_resources_blocks_cgnat_and_other_non_global_ranges():
    # 100.64.0.0/10 non è né is_private né is_reserved: serve il catch-all su is_global.
    checked = check_resources(
        [{"type": "WMS", "url": "http://100.64.0.1/service", "source": "links_s"}],
        timeout=1,
    )
    assert checked[0]["ok"] is False
    assert checked[0]["status_code"] is None
    assert checked[0]["error"] == "url-blocked:non-global-address-not-allowed"


def test_check_resources_blocks_when_dns_resolution_fails(monkeypatch):
    def _fake_getaddrinfo(host: str, port: object, proto: int):  # type: ignore[no-untyped-def]
        raise socket.gaierror("temporary failure in name resolution")

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    checked = check_resources(
        [{"type": "WMS", "url": "https://unresolvable.test/service", "source": "links_s"}],
        timeout=1,
    )
    assert checked[0]["ok"] is False
    assert checked[0]["status_code"] is None
    assert checked[0]["error"] == "url-blocked:dns-resolution-failed"


@respx.mock
def test_check_resources_blocks_redirect_to_non_public_host():
    respx.head("https://redir.test/service").mock(
        return_value=httpx.Response(302, headers={"Location": "http://169.254.1.10/internal"})
    )
    checked = check_resources(
        [{"type": "WMS", "url": "https://redir.test/service", "source": "links_s"}],
        timeout=1,
    )
    assert checked[0]["status_code"] == 302
    # 3xx verso host non pubblico: non seguito, ok=False con errore esplicito.
    assert checked[0]["ok"] is False
    assert checked[0]["redirect_url"] == "http://169.254.1.10/internal"
    assert checked[0]["error"] == "redirect-blocked:link-local-not-allowed"
    assert checked[0]["redirected"] is False


@respx.mock
def test_check_resources_follows_redirect_to_public_host():
    respx.head("https://redir.test/service").mock(
        return_value=httpx.Response(301, headers={"Location": "https://final.test/wms?service=WMS"})
    )
    respx.head("https://final.test/wms?service=WMS").mock(return_value=httpx.Response(200))
    checked = check_resources(
        [{"type": "WMS", "url": "https://redir.test/service", "source": "links_s"}],
        timeout=1,
    )
    row = checked[0]
    # http→https reale: il 301 non è più dichiarato rotto, la probe segue e verifica.
    assert row["ok"] is True
    assert row["status_code"] == 200
    assert row["final_url"] == "https://final.test/wms?service=WMS"
    assert row["redirected"] is True
    assert row["redirect_count"] == 1
    assert row["redirect_url"] == "https://final.test/wms?service=WMS"
    assert isinstance(row["latency_ms"], int)


@respx.mock
def test_check_resources_stops_after_max_redirects():
    def _chain(request: httpx.Request) -> httpx.Response:
        from urllib.parse import urlparse

        path = urlparse(str(request.url)).path
        n = int(path.lstrip("/") or "0")
        return httpx.Response(302, headers={"Location": f"/{n + 1}"})

    respx.route(host="chain.test", method="HEAD").mock(side_effect=_chain)
    checked = check_resources(
        [{"type": "WMS", "url": "https://chain.test/0", "source": "links_s"}],
        timeout=1,
    )
    row = checked[0]
    assert row["error"] == "too-many-redirects"
    assert row["redirect_count"] == _MAX_REDIRECTS
    assert row["ok"] is False


@respx.mock
def test_check_resources_reports_latency(monkeypatch):
    """`latency_ms` è in millisecondi: `perf_counter` conta secondi."""
    respx.head("https://latency.test/wms").mock(return_value=httpx.Response(200))
    ticks = iter([10.0, 10.25])  # 250 ms di probe

    class _FakeTime:
        # Solo il `time` di resources: patchare il modulo globale romperebbe httpx.
        perf_counter = staticmethod(lambda: next(ticks))

    monkeypatch.setattr(resources_module, "time", _FakeTime)
    checked = check_resources(
        [{"type": "WMS", "url": "https://latency.test/wms", "source": "links_s"}],
        timeout=1,
    )
    assert checked[0]["latency_ms"] == 250
