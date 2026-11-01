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
            "source": "resources_nst",
        },
        {
            "type": "WFS",
            "url": "https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php?SERVICE=WFS&REQUEST=GetCapabilities&VERSION=2.0.0",
            "source": "resources_nst",
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
    respx.get("https://down.test/wms?service=WMS").mock(side_effect=httpx.ConnectError("down"))
    checked = check_resources(
        [{"type": "WMS", "url": "https://down.test/wms?service=WMS", "source": "links_s"}],
        timeout=1,
    )
    assert checked[0]["ok"] is False
    assert checked[0]["status_code"] is None
    assert checked[0]["error"] == "ConnectError"
    # HEAD fallita per rete → riprovato in GET: è l'ultimo metodo tentato
    assert checked[0]["method"] == "GET"


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
    # `final_url` è l'ultimo URL davvero probato, non la destinazione rifiutata.
    assert checked[0]["final_url"] == "https://redir.test/service"


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


@respx.mock
def test_check_resources_falls_back_to_get_when_head_connection_is_reset():
    # GeoServer dietro proxy: HEAD chiude la connessione, GET risponde 200.
    respx.head("https://reset.test/geoserver/wms").mock(side_effect=httpx.ReadError("reset"))
    respx.get("https://reset.test/geoserver/wms").mock(return_value=httpx.Response(200))
    checked = check_resources(
        [{"type": "WMS", "url": "https://reset.test/geoserver/wms", "source": "links_s"}],
        timeout=1,
    )
    assert checked[0]["status_code"] == 200
    assert checked[0]["ok"] is True
    assert checked[0]["method"] == "GET"
    assert checked[0]["error"] is None


@respx.mock
def test_check_resources_does_not_retry_get_after_head_timeout():
    respx.head("https://slow.test/wms").mock(side_effect=httpx.ReadTimeout("slow"))
    get_route = respx.get("https://slow.test/wms").mock(return_value=httpx.Response(200))
    checked = check_resources(
        [{"type": "WMS", "url": "https://slow.test/wms", "source": "links_s"}],
        timeout=1,
    )
    assert checked[0]["ok"] is False
    assert checked[0]["error"] == "ReadTimeout"
    assert checked[0]["method"] == "HEAD"
    assert not get_route.called


# --- layer dei servizi WMS (issue #30) ---------------------------------------

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from openrndt.resources import (  # noqa: E402
    capabilities_url,
    list_layers,
    parse_wms_capabilities,
    service_base_url,
    wms_layer_crs,
)

FIXTURES = Path(__file__).parent / "fixtures"
AGEA_ID = "r_emiro:2022-03-11T113115"
AGEA_WMS = "https://servizigis.regione.emilia-romagna.it/wms/agea2020_rgb"
AGEA_CAPS = f"{AGEA_WMS}?SERVICE=WMS&REQUEST=GetCapabilities"


def _caps(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_service_base_url_keeps_mapserver_map_param():
    url = "http://wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/raster/x.map&SERVICE=WMS&request=GetCapabilities&version=1.3.0"
    assert service_base_url(url) == "http://wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/raster/x.map"
    assert capabilities_url(url) == f"{service_base_url(url)}&SERVICE=WMS&REQUEST=GetCapabilities"
    assert capabilities_url(f"{AGEA_WMS}?request=GetCapabilities&service=WMS") == AGEA_CAPS


def test_parse_wms_capabilities_real_agea():
    caps = parse_wms_capabilities(_caps("wms_caps_agea2020_rgb.xml"))
    assert caps["version"] == "1.3.0"
    # `default` è il nome di uno stile, non di un layer
    assert [layer["name"] for layer in caps["layers"]] == ["Agea2020_RGB"]


def test_parse_wms_capabilities_real_pcn_mapserver():
    caps = parse_wms_capabilities(_caps("wms_caps_pcn_messina.xml"))
    names = [layer["name"] for layer in caps["layers"]]
    assert names == ["OI.ORTOIMMAGINICOLORE.ALLUVIONE.MESSINA.33", "OI.DATEVOLO.ALLUVIONE.MESSINA.33"]
    assert "EPSG:3857" in caps["layers"][0]["crs"]
    assert caps["layers"][0]["bbox"] == [15.3871, 38.0182, 15.5482, 38.1634]


WMS_111 = """<?xml version="1.0"?>
<!DOCTYPE WMT_MS_Capabilities SYSTEM "x.dtd" [ <!ELEMENT VendorSpecificCapabilities EMPTY> ]>
<WMT_MS_Capabilities version="1.1.1"><Capability>
<Layer><Title>Radice</Title><SRS>EPSG:32633</SRS>
  <LatLonBoundingBox minx="12" miny="37" maxx="16" maxy="39"/>
  <Layer><Name>gruppo</Name><Title>Gruppo</Title><inspire_vs:x/>
    <Layer><Name>foglia</Name><SRS>CRS:84</SRS></Layer>
  </Layer>
</Layer></Capability></WMT_MS_Capabilities>"""


def test_parse_wms_capabilities_111_inherits_and_repairs():
    # DOCTYPE con subset interno e prefisso non dichiarato: riparati come nel plugin
    caps = parse_wms_capabilities(WMS_111)
    assert caps["version"] == "1.1.1"
    gruppo, foglia = caps["layers"]
    assert (gruppo["name"], gruppo["group"], gruppo["crs"]) == ("gruppo", True, ["EPSG:32633"])
    assert (foglia["title"], foglia["crs"], foglia["bbox"]) == ("foglia", ["EPSG:32633", "CRS:84"], [12.0, 37.0, 16.0, 39.0])


def test_parse_wms_capabilities_service_exception():
    xml = '<ServiceExceptionReport version="1.3.0"><ServiceException>msShapefileOpen(): Unable to access file.</ServiceException></ServiceExceptionReport>'
    with pytest.raises(ValueError, match="Errore del servizio: msShapefileOpen"):
        parse_wms_capabilities(xml)
    with pytest.raises(ValueError, match="XML valido"):
        parse_wms_capabilities("<html><body>Not found")


@pytest.mark.parametrize(
    ("crs", "version", "expected"),
    [
        (["EPSG:25832", "EPSG:3857"], "1.3.0", "EPSG:3857"),
        (["EPSG:900913"], "1.1.1", "EPSG:3857"),
        (["EPSG:32633", "EPSG:4326"], "1.3.0", "EPSG:4326"),
        (["CRS:84", "EPSG:32633"], "1.1.1", "EPSG:32633"),  # CRS:84 solo in 1.3.0
        (["EPSG:25833"], "1.3.0", "EPSG:25833"),  # solo UTM: il plugin lo aggiunge lo stesso
        (["AUTO:42001"], "1.3.0", None),
    ],
)
def test_wms_layer_crs_follows_plugin_rule(crs, version, expected):
    assert wms_layer_crs({"crs": crs}, version) == expected


@respx.mock
def test_list_layers_one_service_per_base_url():
    route = respx.get(AGEA_CAPS).mock(return_value=httpx.Response(200, text=_caps("wms_caps_agea2020_rgb.xml")))
    rows = list_layers(
        AGEA_ID,
        [
            {"type": "WMS", "url": f"{AGEA_WMS}?request=GetCapabilities&service=WMS", "source": "resources_nst"},
            {"type": "WMS", "url": AGEA_WMS.replace("https", "http"), "source": "links_s"},
            {"type": "WFS", "url": "https://example.test/wfs", "source": "links_s"},
        ],
        timeout=1,
    )
    assert route.call_count == 1
    assert rows == [
        {
            "service": AGEA_WMS,
            "kind": "wms",
            "name": "Agea2020_RGB",
            "title": "Agea2020_RGB",
            "crs": "EPSG:3857",
            "tile_url": None,
            "cors": None,
            "geolibre_url": "https://web.geolibre.app/?plugin=openrndt-geolibre&rndt=r_emiro%3A2022-03-11T113115"
            "&rndtLayer=r_emiro%3A2022-03-11T113115~wms~Agea2020_RGB",
            "note": None,
            "error": None,
        }
    ]


@respx.mock
def test_list_layers_reports_errors_http_and_duplicate_names():
    respx.get("https://a.test/wms?SERVICE=WMS&REQUEST=GetCapabilities").mock(return_value=httpx.Response(500))
    respx.get("http://b.test/wms?SERVICE=WMS&REQUEST=GetCapabilities").mock(
        return_value=httpx.Response(200, text=WMS_111.replace("<SRS>EPSG:32633</SRS>", "<SRS>AUTO:42001</SRS>"))
    )
    respx.get("https://c.test/wms?SERVICE=WMS&REQUEST=GetCapabilities").mock(
        return_value=httpx.Response(200, text=WMS_111)
    )
    rows = list_layers(
        "x:1",
        [
            {"type": "WMS", "url": "https://a.test/wms", "source": "links_s"},
            {"type": "WMS", "url": "http://b.test/wms", "source": "links_s"},
            {"type": "WMS", "url": "https://c.test/wms", "source": "links_s"},
        ],
        timeout=1,
    )
    assert [(r["service"], r["name"], r["error"]) for r in rows] == [
        ("https://a.test/wms", None, "HTTP 500"),
        ("http://b.test/wms", "gruppo", None),
        ("http://b.test/wms", "foglia", None),
        ("https://c.test/wms", "gruppo", None),
        ("https://c.test/wms", "foglia", None),
    ]
    gruppo_b, foglia_b, gruppo_c, foglia_c = rows[1:]
    # nessun CRS utile: il plugin rifiuterebbe il layer
    assert gruppo_b["geolibre_url"] is None and gruppo_b["note"] == "nessun CRS che GeoLibre sa disegnare"
    # CRS:84 non vale in 1.1.1, AUTO nemmeno
    assert foglia_b["geolibre_url"] is None
    # nomi già visti: il plugin si ferma al primo servizio che li elenca
    assert gruppo_c["geolibre_url"] is None and "servizio precedente" in gruppo_c["note"]
    assert foglia_c["geolibre_url"] is None


@respx.mock
def test_list_layers_http_service_gets_note():
    respx.get("http://b.test/wms?SERVICE=WMS&REQUEST=GetCapabilities").mock(
        return_value=httpx.Response(200, text=WMS_111)
    )
    rows = list_layers("x:1", [{"type": "WMS", "url": "http://b.test/wms", "source": "links_s"}], timeout=1)
    assert rows[0]["geolibre_url"] is not None
    assert rows[0]["note"].startswith("servizio in http://")


def test_list_layers_blocks_private_hosts():
    rows = list_layers("x:1", [{"type": "WMS", "url": "http://127.0.0.1/wms", "source": "links_s"}], timeout=1)
    assert rows[0]["error"] == "url-blocked:loopback-not-allowed"


@respx.mock
def test_list_layers_blocks_redirect_to_private_host():
    respx.get("https://a.test/wms?SERVICE=WMS&REQUEST=GetCapabilities").mock(
        return_value=httpx.Response(302, headers={"location": "http://10.0.0.1/caps"})
    )
    rows = list_layers("x:1", [{"type": "WMS", "url": "https://a.test/wms", "source": "links_s"}], timeout=1)
    assert rows[0]["error"].startswith("url-blocked:")


def test_parse_wms_capabilities_reads_declared_encoding():
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<WMS_Capabilities version="1.3.0"><Capability><Layer><CRS>EPSG:3857</CRS>
<Layer><Name>c</Name><Title>Città</Title></Layer></Layer></Capability></WMS_Capabilities>""".encode("latin-1")
    assert parse_wms_capabilities(xml)["layers"][0]["title"] == "Città"


def test_parse_wms_capabilities_repairs_without_breaking_declared_encoding():
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<WMS_Capabilities version="1.3.0"><Capability><Layer><CRS>EPSG:3857</CRS><foo:x/>
<Layer><Name>città</Name><Title>Città</Title></Layer></Layer></Capability></WMS_Capabilities>""".encode("latin-1")
    layer = parse_wms_capabilities(xml)["layers"][0]
    assert (layer["name"], layer["title"]) == ("città", "Città")


def test_parse_wms_capabilities_unknown_encoding_and_deep_nesting_are_value_errors():
    with pytest.raises(ValueError):
        parse_wms_capabilities(b'<?xml version="1.0" encoding="x-nope"?><a/>')
    deep = "<WMS_Capabilities version=\"1.3.0\"><Capability>" + "<Layer><Name>n</Name>" * 1200 + "</Layer>" * 1200
    with pytest.raises(ValueError):
        parse_wms_capabilities((deep + "</Capability></WMS_Capabilities>").encode())


@respx.mock
def test_list_layers_bad_service_is_an_error_row():
    respx.get("https://a.test/wms?SERVICE=WMS&REQUEST=GetCapabilities").mock(
        return_value=httpx.Response(200, content=b'<?xml version="1.0" encoding="x-nope"?><a/>')
    )
    rows = list_layers("x:1", [{"type": "WMS", "url": "https://a.test/wms", "source": "links_s"}], timeout=1)
    assert rows[0]["name"] is None and rows[0]["error"]


@respx.mock
def test_list_layers_prefers_https_variant():
    route = respx.get("https://a.test/wms?SERVICE=WMS&REQUEST=GetCapabilities").mock(
        return_value=httpx.Response(200, text=WMS_111)
    )
    rows = list_layers(
        "x:1",
        [
            {"type": "WMS", "url": "http://a.test/wms", "source": "links_s"},
            {"type": "WMS", "url": "https://a.test/wms?request=GetCapabilities", "source": "links_s"},
        ],
        timeout=1,
    )
    assert route.call_count == 1
    assert {r["service"] for r in rows} == {"https://a.test/wms"}
    assert all(r["note"] is None or "http://" not in r["note"] for r in rows)


def test_extract_resources_wmts_from_url_beats_declared_type():
    """AGEA: `url_type_s` "ImageServer" su un URL `…/ImageServer/WMTS?` → WMTS."""
    url = "https://geoportale.agea.gov.it/image/rest/services/AgEA/Ortofoto_AgEA_2022/ImageServer/WMTS?"
    payload = {"_source": {"resources_nst": [{"url_s": url, "url_type_s": "ImageServer"}], "links_s": [url]}}
    assert extract_resources(payload) == [{"type": "WMTS", "url": url, "source": "resources_nst"}]


@pytest.mark.parametrize(
    "url",
    [
        "https://x.it/arcgis/rest/services/A/MapServer/WMTS/1.0.0/WMTSCapabilities.xml",
        "https://idt2.regione.veneto.it/gwc/service/wmts",
        "https://geoservices.buergernetz.bz.it/mapproxy/service?REQUEST=GetCapabilities&SERVICE=WMTS",
    ],
)
def test_extract_resources_wmts_inferred_from_bare_urls(url):
    """URL nudi in `links_s`: WMTS dal path (anche prima dell'estensione `.xml`) o da `SERVICE=WMTS`."""
    assert extract_resources({"_source": {"links_s": [url]}})[0]["type"] == "WMTS"


def test_extract_resources_service_wms_on_wmts_host_stays_wms():
    """`wmts` nel nome host non conta: `SERVICE=WMS` resta WMS."""
    url = "https://wmtscatasto-gis.csi.it/mapproxy/service?request=GetCapabilities&service=WMS"
    assert extract_resources({"_source": {"links_s": [url]}})[0]["type"] == "WMS"


# --- layer dei servizi WMTS ---------------------------------------------------

from openrndt.resources import (  # noqa: E402
    best_matching_layer,
    parse_wmts_capabilities,
    plan_wmts_layer,
    preselected_name,
    upgrade_to_https,
    web_mercator_zooms,
    wmts_capabilities_url,
    wmts_probe_url,
)

AGEA22_ID = "agea:OI:DATEVOLO:m001+-++-+2026-09-25+12:42:55"
AGEA22_WMTS = "https://geoportale.agea.gov.it/image/rest/services/AgEA/Ortofoto_AgEA_2022/ImageServer/WMTS"
AGEA22_TEMPLATE = f"{AGEA22_WMTS}/tile/1.0.0/AgEA_Ortofoto_AgEA_2022/default/GoogleMapsCompatible/{{z}}/{{y}}/{{x}}"


def _wmts(name: str) -> dict:
    return parse_wmts_capabilities((FIXTURES / name).read_bytes())


def test_wmts_capabilities_url_static_xml_or_kvp():
    static = f"{AGEA22_WMTS}/1.0.0/WMTSCapabilities.xml"
    assert wmts_capabilities_url(static) == static
    assert wmts_capabilities_url(f"{AGEA22_WMTS}?") == f"{AGEA22_WMTS}?SERVICE=WMTS&REQUEST=GetCapabilities"


def test_wmts_agea_arcgis_restful_google_maps_compatible():
    """ArcGIS ImageServer: griglia GoogleMapsCompatible scelta prima di default028mm, template RESTful."""
    caps = _wmts("wmts_caps_agea2022.xml")
    layer = caps["layers"][0]
    assert layer["name"] == "AgEA_Ortofoto_AgEA_2022"
    assert layer["style"] == "default"
    plan = plan_wmts_layer(caps, layer)
    assert plan["ok"] and plan["set"] == "GoogleMapsCompatible"
    assert plan["template"] == AGEA22_TEMPLATE
    assert (plan["minzoom"], plan["maxzoom"]) == (0, 18)


def test_wmts_veneto_geowebcache_kvp_prefixed_ids():
    """GeoWebCache: `EPSG:900913` con id `EPSG:900913:<z>`, angolo arrotondato, solo GetTile KVP."""
    caps = _wmts("wmts_caps_veneto_gwc.xml")
    assert web_mercator_zooms(caps["sets"]["EPSG:900913"])[0] == "EPSG:900913:"
    gm, national = caps["layers"]
    plan = plan_wmts_layer(caps, gm)
    assert plan["ok"] and plan["set"] == "EPSG:900913"
    assert "REQUEST=GetTile" in plan["template"] and "TILEMATRIX=EPSG%3A900913%3A{z}" in plan["template"]
    assert plan["template"].startswith("http://idt2.regione.veneto.it/")  # come lo dichiara il server
    assert plan_wmts_layer(caps, national) == {"ok": False, "reason": "no-web-mercator", "systems": ["EPSG:3003"]}


def test_wmts_bolzano_zero_padded_ids_not_addressable():
    """MapProxy di Bolzano: `EPSG_3857` con id `00`, `01`…: GeoLibre non sa indirizzarli."""
    caps = _wmts("wmts_caps_bz_mapproxy.xml")
    assert web_mercator_zooms(caps["sets"]["EPSG_3857"]) == "matrix-ids"
    plan = plan_wmts_layer(caps, caps["layers"][0])
    assert plan["ok"] is False and plan["reason"] == "matrix-ids"
    assert "EPSG:3857" in plan["systems"]


def test_wmts_csi_utm_only():
    caps = _wmts("wmts_caps_csi_agea2015.xml")
    plan = plan_wmts_layer(caps, caps["layers"][0])
    assert plan == {"ok": False, "reason": "no-web-mercator", "systems": ["EPSG:32632"]}


def test_wmts_template_with_unfillable_placeholder():
    caps = _wmts("wmts_caps_agea2022.xml")
    layer = caps["layers"][0]
    layer["templates"] = [{"format": "image/png", "template": "https://x.it/{Time}/{TileMatrix}/{TileRow}/{TileCol}"}]
    assert plan_wmts_layer(caps, layer)["reason"] == "template"


def test_parse_wmts_capabilities_rejects_wms_and_exceptions():
    with pytest.raises(ValueError):
        parse_wmts_capabilities(_caps("wms_caps_agea2020_rgb.xml"))
    with pytest.raises(ValueError, match="Errore del servizio"):
        parse_wmts_capabilities("<ExceptionReport><Exception>boom</Exception></ExceptionReport>")


def test_upgrade_to_https_same_host_only():
    fetched = "https://idt2.regione.veneto.it/gwc/service/wmts?SERVICE=WMTS&REQUEST=GetCapabilities"
    assert upgrade_to_https("http://idt2.regione.veneto.it/gwc/service/wmts?x=1", fetched) == (
        "https://idt2.regione.veneto.it/gwc/service/wmts?x=1"
    )
    assert upgrade_to_https("http://altro.it/wmts", fetched) == "http://altro.it/wmts"
    assert upgrade_to_https("http://idt2.regione.veneto.it/a", fetched.replace("https", "http")).startswith("http://")


def test_wmts_probe_url_inside_extent():
    url = wmts_probe_url("https://t/{z}/{y}/{x}", [13.0, 38.0, 13.5, 38.3], 0, 18)
    assert url == "https://t/11/788/1099"


def test_preselected_name_and_best_matching_layer():
    assert preselected_name("https://a.it/wms?SERVICE=WMS&LAYERS=uno,due") == "uno"
    assert preselected_name("https://a.it/wms?SERVICE=WMS") is None
    layers = [{"name": "rv:ctr", "title": "Carta tecnica"}, {"name": "rv:orto", "title": "Ortofoto 2021 Veneto"}]
    assert best_matching_layer("Ortofoto del Veneto 2021", layers) == "rv:orto"
    assert best_matching_layer("Niente in comune", layers) is None


@respx.mock
def test_list_layers_wmts_with_cors_gives_geolibre_url():
    respx.get(f"{AGEA22_WMTS}?SERVICE=WMTS&REQUEST=GetCapabilities").mock(
        return_value=httpx.Response(200, content=(FIXTURES / "wmts_caps_agea2022.xml").read_bytes())
    )
    tile = respx.get(url__startswith=f"{AGEA22_WMTS}/tile/").mock(
        return_value=httpx.Response(200, content=b"jpg", headers={"Access-Control-Allow-Origin": "https://web.geolibre.app"})
    )
    rows = list_layers(AGEA22_ID, [{"type": "WMTS", "url": f"{AGEA22_WMTS}?", "source": "resources_nst"}], timeout=1)
    assert tile.calls.last.request.headers["Origin"] == "https://web.geolibre.app"
    assert rows == [
        {
            "service": AGEA22_WMTS,
            "kind": "wmts",
            "name": "AgEA_Ortofoto_AgEA_2022",
            "title": "AgEA_Ortofoto_AgEA_2022",
            "crs": "EPSG:3857",
            "tile_url": AGEA22_TEMPLATE,
            "cors": True,
            "geolibre_url": "https://web.geolibre.app/?plugin=openrndt-geolibre"
            "&rndt=agea%3AOI%3ADATEVOLO%3Am001%2B-%2B%2B-%2B2026-09-25%2B12%3A42%3A55"
            "&rndtLayer=agea%3AOI%3ADATEVOLO%3Am001%2B-%2B%2B-%2B2026-09-25%2B12%3A42%3A55~wmts~AgEA_Ortofoto_AgEA_2022",
            "note": None,
            "error": None,
        }
    ]


@respx.mock
def test_list_layers_wmts_without_cors_no_link():
    respx.get(f"{AGEA22_WMTS}?SERVICE=WMTS&REQUEST=GetCapabilities").mock(
        return_value=httpx.Response(200, content=(FIXTURES / "wmts_caps_agea2022.xml").read_bytes())
    )
    respx.get(url__startswith=f"{AGEA22_WMTS}/tile/").mock(return_value=httpx.Response(200, content=b"jpg"))
    row = list_layers(AGEA22_ID, [{"type": "WMTS", "url": f"{AGEA22_WMTS}?", "source": "links_s"}], timeout=1)[0]
    assert row["cors"] is False and row["geolibre_url"] is None
    assert "CORS" in row["note"]


@respx.mock
def test_list_layers_wmts_upgrades_declared_http_and_skips_national():
    """Veneto: GetTile dichiarato in http, capabilities lette in https → tile in https; il layer solo EPSG:3003 ha la nota."""
    base = "https://idt2.regione.veneto.it/gwc/service/wmts"
    respx.get(f"{base}?SERVICE=WMTS&REQUEST=GetCapabilities").mock(
        return_value=httpx.Response(200, content=(FIXTURES / "wmts_caps_veneto_gwc.xml").read_bytes())
    )
    tile = respx.get(url__startswith=f"{base}?SERVICE=WMTS&REQUEST=GetTile").mock(
        return_value=httpx.Response(200, content=b"png", headers={"Access-Control-Allow-Origin": "*"})
    )
    gm, national = list_layers("r_veneto:x", [{"type": "WMTS", "url": base, "source": "links_s"}], timeout=1)
    assert tile.called
    assert gm["tile_url"].startswith("https://") and gm["geolibre_url"].endswith("~wmts~rv%3Actr_128_bicubic")
    assert national["geolibre_url"] is None and "EPSG:3003" in national["note"]


@respx.mock
def test_list_layers_wmts_tile_error_no_link():
    respx.get(f"{AGEA22_WMTS}?SERVICE=WMTS&REQUEST=GetCapabilities").mock(
        return_value=httpx.Response(200, content=(FIXTURES / "wmts_caps_agea2022.xml").read_bytes())
    )
    respx.get(url__startswith=f"{AGEA22_WMTS}/tile/").mock(return_value=httpx.Response(404))
    row = list_layers(AGEA22_ID, [{"type": "WMTS", "url": f"{AGEA22_WMTS}?", "source": "links_s"}], timeout=1)[0]
    assert row["cors"] is None and row["geolibre_url"] is None
    assert "tile HTTP 404" in row["note"]



def _row(kind, name, crs="EPSG:3857", service="https://s.it/wms", url="x"):
    return {"kind": kind, "name": name, "title": name, "crs": crs, "service": service, "geolibre_url": url}


def test_pick_map_layer_rules():
    from openrndt.resources import pick_map_layer

    rows = [
        _row("wms", "a:strade"),
        _row("wms", "a:fiumi"),
        _row("wms", "a:http", service="http://s.it/wms"),
        _row("wms", "a:utm", crs="EPSG:32632"),
        _row("wms", "a:none", url=None),
    ]
    getmap = [{"type": "WMS", "url": "https://s.it/wms?REQUEST=GetMap&LAYERS=a:fiumi"}]
    assert pick_map_layer(rows, getmap)["name"] == "a:fiumi"
    assert pick_map_layer(rows, [], title="Rete dei fiumi")["name"] == "a:fiumi"
    assert pick_map_layer(rows, [], title="Niente") is None
    assert pick_map_layer(rows, [], title="Rete dei fiumi", record_type="service") is None
    assert pick_map_layer(rows[2:], [], title="x") is None
    assert pick_map_layer([_row("wmts", "o", crs="EPSG:3857")], [])["name"] == "o"



def test_web_mercator_zooms_rejects_nan_scale():
    """`ScaleDenominator` "NaN" passa `float()`: la griglia non è usabile, niente eccezione."""
    caps = _wmts("wmts_caps_agea2022.xml")
    caps["sets"]["GoogleMapsCompatible"]["matrices"][0]["scale"] = float("nan")
    assert web_mercator_zooms(caps["sets"]["GoogleMapsCompatible"]) is None
    assert plan_wmts_layer(caps, caps["layers"][0])["ok"] is True  # resta default028mm


@respx.mock
def test_list_layers_wmts_nan_everywhere_no_crash():
    xml = (FIXTURES / "wmts_caps_agea2022.xml").read_text(encoding="utf-8")
    import re

    xml = re.sub(r"<ScaleDenominator>[^<]*</ScaleDenominator>", "<ScaleDenominator>NaN</ScaleDenominator>", xml)
    respx.get(f"{AGEA22_WMTS}?SERVICE=WMTS&REQUEST=GetCapabilities").mock(return_value=httpx.Response(200, text=xml))
    row = list_layers(AGEA22_ID, [{"type": "WMTS", "url": f"{AGEA22_WMTS}?", "source": "links_s"}], timeout=1)[0]
    assert row["geolibre_url"] is None and "Web Mercator" in row["note"]


@respx.mock
def test_tile_cors_follows_redirect_and_reads_final_response():
    from openrndt.resources import tile_cors

    respx.get("https://a.test/tile/1/2/3").mock(
        return_value=httpx.Response(302, headers={"location": "https://b.test/t.png", "Access-Control-Allow-Origin": "*"})
    )
    respx.get("https://b.test/t.png").mock(return_value=httpx.Response(200, content=b"png"))
    assert tile_cors("https://a.test/tile/1/2/3", 1) == (False, None)


def test_tile_cors_blocks_redirect_to_private_host():
    from openrndt.resources import tile_cors

    with respx.mock:
        respx.get("https://a.test/tile").mock(return_value=httpx.Response(302, headers={"location": "http://10.0.0.1/t"}))
        cors, error = tile_cors("https://a.test/tile", 1)
    assert cors is None and error.startswith("url-blocked:")
