"""Estrazione e verifica rapida delle risorse fruibili di un metadato RNDT."""

from __future__ import annotations

import ipaddress
import math
import re
import socket
import ssl
import time
import unicodedata
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import (
    parse_qs,
    parse_qsl,
    quote,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)

import httpx

from openrndt.client import USER_AGENT
from openrndt.config import get_timeout

_NON_RESOURCE_RELS = {"alternate", "icon", "self"}
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_MAX_REDIRECTS = 3


def _probe_ssl_context() -> ssl.SSLContext:
    """Contesto TLS per la sola probe di raggiungibilità.

    Diversi server OGC di enti pubblici (es. sgi2.isprambiente.it, GeoServer)
    negoziano solo TLS 1.2 con cifrature legacy (`AES128-SHA`) che il livello
    di sicurezza predefinito di OpenSSL (SECLEVEL=2) rifiuta: httpx ottiene
    `Connection reset by peer` mentre curl risponde 200. Qui non si trasferiscono
    dati sensibili, si chiede solo se il servizio è vivo: abbassare il livello
    evita falsi negativi. Certificato e hostname restano verificati.
    """
    ctx = ssl.create_default_context()
    ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    return ctx


_PROBE_SSL_CONTEXT = _probe_ssl_context()
_DOWNLOAD_EXTENSIONS = {
    ".csv",
    ".geojson",
    ".gpkg",
    ".gz",
    ".json",
    ".jsonl",
    ".kml",
    ".kmz",
    ".pdf",
    ".shp",
    ".tif",
    ".tiff",
    ".tsv",
    ".xml",
    ".zip",
}


def _normalize_url_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


def _infer_kind(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    service = query.get("SERVICE") or query.get("service")
    if service and service[0]:
        return service[0].upper()

    path_lower = parsed.path.lower()
    # Prima delle estensioni: `…/WMTS/1.0.0/WMTSCapabilities.xml` è un WMTS, non un download.
    if "/wmts" in path_lower:
        return "WMTS"
    if path_lower.endswith(tuple(_DOWNLOAD_EXTENSIONS)):
        return "download"
    if "wms" in path_lower:
        return "WMS"
    if "wfs" in path_lower:
        return "WFS"
    if "wcs" in path_lower:
        return "WCS"
    if "wmts" in path_lower:
        return "WMTS"
    return "link"


def _normalize_kind(kind: str) -> str:
    raw = kind.strip()
    if not raw:
        return "link"
    up = raw.upper()
    if up in {"WMS", "WFS", "WCS", "WMTS"}:
        return up
    if up == "DOWNLOAD":
        return "download"
    if up == "LINK":
        return "link"
    return raw


def _blocked_host_reason(hostname: str | None) -> str | None:
    if not hostname:
        return "missing-hostname"
    host = hostname.strip().lower()
    if host == "localhost" or host.endswith(".localhost"):
        return "localhost-not-allowed"
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return None
    if addr.is_loopback:
        return "loopback-not-allowed"
    if addr.is_link_local:
        return "link-local-not-allowed"
    if addr.is_private:
        return "private-address-not-allowed"
    if addr.is_reserved:
        return "reserved-address-not-allowed"
    if addr.is_unspecified:
        return "unspecified-address-not-allowed"
    if addr.is_multicast:
        return "multicast-address-not-allowed"
    # Catch-all per i range special-purpose non coperti dai predicati sopra
    # (es. CGNAT 100.64.0.0/10, che non è né private né reserved).
    if not addr.is_global:
        return "non-global-address-not-allowed"
    return None


def _blocked_resolved_hostname_reason(hostname: str) -> str | None:
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        # Non risolvibile = non validabile: si blocca, non si lascia passare.
        return "dns-resolution-failed"
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_str = str(sockaddr[0])
        reason = _blocked_host_reason(ip_str)
        if reason is not None:
            return f"dns-resolves-to-{reason}"
    return None


def _validate_check_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "unsupported-scheme"
    hostname = parsed.hostname
    reason = _blocked_host_reason(hostname)
    if reason is not None:
        return reason
    if hostname is None:
        return "missing-hostname"
    return _blocked_resolved_hostname_reason(hostname)


def extract_resources(item_payload: dict[str, Any]) -> list[dict[str, str]]:
    """Estrae e deduplica risorse utili (WMS/WFS/.../download) dal payload item.

    Fonti in ordine di affidabilità: ``resources_nst`` (tipi assegnati dal
    catalogo), ``links`` (dctype dichiarato nel metadato), ``webServices_s`` e
    ``links_s`` (URL nude, tipo dedotto dall'URL). Deduplica per URL: vince la
    prima fonte che presenta l'indirizzo.
    """
    source = item_payload.get("_source") or {}
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    for entry in source.get("resources_nst") or []:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url_s")
        if not isinstance(url, str) or not url or url in seen:
            continue
        declared = entry.get("url_type_s")
        kind = _normalize_kind(declared) if isinstance(declared, str) else "link"
        if kind == "link" or _infer_kind(url) == "WMTS":
            # L'URL che dice WMTS vince sul tipo dichiarato: le ortofoto AGEA
            # hanno `url_type_s` "ImageServer" su un `…/ImageServer/WMTS?`.
            kind = _normalize_kind(_infer_kind(url))
        seen.add(url)
        rows.append({"type": kind, "url": url, "source": "resources_nst"})

    for link in (item_payload.get("links") or []):
        if not isinstance(link, dict):
            continue
        rel = link.get("rel")
        href = link.get("href")
        if not isinstance(href, str) or rel in _NON_RESOURCE_RELS:
            continue
        kind_raw = link.get("dctype")
        kind = _normalize_kind(kind_raw) if isinstance(kind_raw, str) else _normalize_kind(_infer_kind(href))
        if _infer_kind(href) == "WMTS":
            kind = "WMTS"
        if kind == "link":
            continue
        if href in seen:
            continue
        seen.add(href)
        rows.append({"type": kind, "url": href, "source": "links"})

    for key in ("webServices_s", "links_s"):
        for url in _normalize_url_values(source.get(key)):
            kind = _normalize_kind(_infer_kind(url))
            if kind == "link":
                continue
            if url in seen:
                continue
            seen.add(url)
            rows.append({"type": kind, "url": url, "source": key})
    return rows


def _apply_response(row: dict[str, Any], response: httpx.Response, method: str, url: str) -> None:
    row["status_code"] = response.status_code
    row["ok"] = 200 <= response.status_code < 300
    row["final_url"] = str(response.url)
    row["method"] = method


def _probe_once(url: str, headers: dict[str, str], timeout: float) -> tuple[httpx.Response, str, float]:
    """Probe HTTP leggera: HEAD, con fallback GET in streaming sui 4xx/5xx e sugli errori di trasporto.

    Non segue redirect (li gestisce il chiamante, con validazione per hop).
    Ritorna (response, metodo usato, millisecondi trascorsi).
    """
    start = time.perf_counter()
    try:
        response = httpx.head(
            url, headers=headers, timeout=timeout, follow_redirects=False, verify=_PROBE_SSL_CONTEXT
        )
    except httpx.TimeoutException:
        # Un timeout non è un rifiuto della HEAD: riprovare in GET
        # raddoppierebbe l'attesa senza cambiare l'esito.
        raise
    except httpx.TransportError:
        # Alcuni server (es. GeoServer dietro proxy) chiudono la connessione su
        # HEAD e rispondono normalmente a GET: prima di segnare un errore di
        # rete si riprova in streaming (falso negativo visto su
        # sgi2.isprambiente.it/geoserver, 2026-08-30).
        response = None
    elapsed = (time.perf_counter() - start) * 1000
    if response is None or response.status_code >= 400:
        try:
            return _stream_get(url, headers, timeout, start)
        except httpx.HTTPError as exc:
            # Chi legge l'errore deve sapere che l'ultimo tentativo era GET.
            exc.probe_method = "GET"  # type: ignore[attr-defined]
            raise
    return response, "HEAD", elapsed


def _stream_get(
    url: str, headers: dict[str, str], timeout: float, start: float
) -> tuple[httpx.Response, str, float]:
    """GET in streaming, senza scaricare il body.

    HEAD è solo un'ottimizzazione: molti WMS/WFS reali la rifiutano con
    403/405/500 (o chiudono la connessione) pur rispondendo 200 a GET.
    """
    with httpx.stream(
        "GET",
        url,
        headers=headers,
        timeout=timeout,
        follow_redirects=False,
        verify=_PROBE_SSL_CONTEXT,
    ) as stream_response:
        elapsed = (time.perf_counter() - start) * 1000
        return stream_response, "GET", elapsed


def check_resources(resources: list[dict[str, str]], *, timeout: float | None = None) -> list[dict[str, Any]]:
    """Controlla raggiungibilità endpoint con probe leggero (HEAD, fallback GET).

    I redirect (max `_MAX_REDIRECTS`) vengono seguiti solo se la destinazione
    supera la stessa validazione di sicurezza dell'URL iniziale: un 3xx verso un
    host non pubblico (loopback, privato, link-local, DNS verso indirizzi
    riservati, …) non viene seguito e produce `error=redirect-blocked:…`.
    `ok` è True solo per la risposta finale 2xx. Ogni riga riporta `latency_ms`
    (durata complessiva della probe) e, se c'è stato un redirect, `redirected`,
    `redirect_count` e `redirect_url` (prima destinazione).
    """
    if timeout is None:
        timeout = get_timeout()

    checked: list[dict[str, Any]] = []
    headers = {"User-Agent": USER_AGENT}
    for resource in resources:
        row: dict[str, Any] = dict(resource)
        row["status_code"] = None
        row["ok"] = False
        row["final_url"] = resource["url"]
        row["redirect_url"] = None
        row["error"] = None
        row["method"] = "HEAD"
        row["latency_ms"] = None
        row["redirected"] = False
        row["redirect_count"] = 0
        blocked_reason = _validate_check_url(resource["url"])
        if blocked_reason is not None:
            row["error"] = f"url-blocked:{blocked_reason}"
            checked.append(row)
            continue
        current = resource["url"]
        total_ms = 0.0
        for hop in range(_MAX_REDIRECTS + 1):
            try:
                response, method, elapsed = _probe_once(current, headers, timeout)
            except httpx.HTTPError as exc:
                row["error"] = type(exc).__name__
                row["method"] = getattr(exc, "probe_method", "HEAD")
                break
            total_ms += elapsed
            _apply_response(row, response, method, current)
            status = response.status_code
            if status in _REDIRECT_STATUSES:
                location = response.headers.get("location")
                if not location:
                    break
                next_url = urljoin(current, location)
                if next_url == current:
                    break
                if row["redirect_count"] >= _MAX_REDIRECTS:
                    row["error"] = "too-many-redirects"
                    break
                if row["redirect_url"] is None:
                    row["redirect_url"] = next_url
                blocked_reason = _validate_check_url(next_url)
                if blocked_reason is not None:
                    # `final_url` resta l'ultimo URL davvero contattato: la
                    # destinazione rifiutata non è stata probata ed è già in
                    # `redirect_url`.
                    row["error"] = f"redirect-blocked:{blocked_reason}"
                    break
                row["redirected"] = True
                row["redirect_count"] += 1
                current = next_url
                continue
            break
        row["latency_ms"] = round(total_ms) if total_ms else None
        checked.append(row)
    return checked


# --- layer dei servizi WMS (issue #30) ---------------------------------------

# Parametri di operazione tolti per risalire alla base del servizio, come
# `serviceBaseUrl` del plugin openrndt-geolibre: `?map=…` di MapServer resta.
_OPERATION_PARAMS = {
    "service", "request", "version", "acceptversions", "layers", "layer", "typename",
    "typenames", "outputformat", "srs", "crs", "srsname", "bbox", "width", "height",
    "format", "styles", "count", "maxfeatures", "startindex",
}
_MAX_CAPABILITIES_BYTES = 10 * 1024 * 1024
_GEOGRAPHIC_CRS = ("EPSG:4326", "EPSG:4258", "EPSG:6706", "CRS:84")


def service_base_url(url: str) -> str:
    """URL del servizio senza i parametri di operazione (SERVICE, REQUEST, LAYERS, …)."""
    parsed = urlparse(url)
    kept = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() not in _OPERATION_PARAMS]
    return urlunparse(parsed._replace(query=urlencode(kept, safe="/:"), fragment=""))


def capabilities_url(url: str) -> str:
    """GetCapabilities WMS del servizio a cui appartiene `url`."""
    base = service_base_url(url)
    return f"{base}{'&' if urlparse(base).query else '?'}SERVICE=WMS&REQUEST=GetCapabilities"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def _child(el: ET.Element, name: str) -> ET.Element | None:
    return next((c for c in el if _local(c.tag) == name), None)


def _children(el: ET.Element, name: str) -> list[ET.Element]:
    return [c for c in el if _local(c.tag) == name]


def _text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


def _repair_xml(xml: str) -> str:
    """Toglie il DOCTYPE e dichiara i prefissi usati senza `xmlns`, come `repairXml` del plugin."""
    xml = re.sub(r"<!DOCTYPE[^[>]*(\[[\s\S]*?\])?\s*>", "", xml, count=1, flags=re.IGNORECASE)
    declared = set(re.findall(r"xmlns:([\w.-]+)\s*=", xml))
    used = {a or b for a, b in re.findall(r"</?([\w.-]+):[\w.-]+|\s([\w.-]+):[\w.-]+\s*=", xml)}
    missing = sorted(p for p in used if p and p not in {"xml", "xmlns"} and p not in declared)
    if not missing:
        return xml
    decls = "".join(f' xmlns:{p}="urn:x-undeclared:{p}"' for p in missing)
    return re.sub(r"<([A-Za-z_][\w.:-]*)", lambda m: m.group(0) + decls, xml, count=1)


def _strip_doctype(xml: bytes) -> bytes:
    return re.sub(rb"<!DOCTYPE[^[>]*(\[[\s\S]*?\])?\s*>", b"", xml, count=1, flags=re.IGNORECASE)


def parse_wms_capabilities(xml: str | bytes) -> dict[str, Any]:
    """Versione e layer con nome di un documento GetCapabilities WMS.

    Ogni layer: ``name``, ``title``, ``crs`` (propri ed ereditati), ``bbox``
    in gradi (``[ovest, sud, est, nord]`` o ``None``), ``group``. Solleva
    ``ValueError`` su XML non valido o su un'eccezione OGC.
    """
    # In byte il parser legge l'encoding dalla dichiarazione XML: molti server
    # della PA servono ISO-8859-1 senza charset nell'intestazione HTTP.
    raw = xml.encode("utf-8") if isinstance(xml, str) else xml
    try:
        root = ET.fromstring(_strip_doctype(raw))
    except ET.ParseError:
        declared = re.search(rb"""<\?xml[^>]*encoding=["']([\w.-]+)""", raw[:200])
        try:
            text = raw.decode(declared.group(1).decode() if declared else "utf-8", errors="replace")
            # Testo già decodificato: la dichiarazione di encoding non conta più.
            root = ET.fromstring(_repair_xml(text))
        except (ET.ParseError, LookupError) as exc:
            raise ValueError("Il servizio non ha restituito XML valido.") from exc
    except LookupError as exc:
        raise ValueError("Il servizio dichiara un encoding sconosciuto.") from exc
    if _local(root.tag) in {"ServiceExceptionReport", "ExceptionReport"}:
        message = " ".join("".join(root.itertext()).split())
        raise ValueError(f"Errore del servizio: {message[:300]}")
    if _local(root.tag) not in {"WMS_Capabilities", "WMT_MS_Capabilities"}:
        raise ValueError("Il documento non è una GetCapabilities WMS.")

    layers: list[dict[str, Any]] = []

    def bbox_of(layer: ET.Element) -> list[float] | None:
        geo = _child(layer, "EX_GeographicBoundingBox")
        if geo is not None:
            values = [_text(_child(geo, n)) for n in ("westBoundLongitude", "southBoundLatitude", "eastBoundLongitude", "northBoundLatitude")]
        else:
            ll = _child(layer, "LatLonBoundingBox")
            if ll is None:
                return None
            values = [ll.get(a, "") for a in ("minx", "miny", "maxx", "maxy")]
        try:
            return [float(v) for v in values]
        except ValueError:
            return None

    def walk(layer: ET.Element, crs: list[str], bbox: list[float] | None) -> None:
        own = [c for el in _children(layer, "CRS") + _children(layer, "SRS") for c in _text(el).split()]
        crs = list(dict.fromkeys(crs + own))
        bbox = bbox_of(layer) or bbox
        children = _children(layer, "Layer")
        name = _text(_child(layer, "Name"))
        if name:
            title = _text(_child(layer, "Title")) or name
            layers.append({"name": name, "title": title, "crs": crs, "bbox": bbox, "group": bool(children)})
        for child in children:
            walk(child, crs, bbox)

    capability = next((el for el in root.iter() if _local(el.tag) == "Capability"), None)
    try:
        for top in _children(capability, "Layer") if capability is not None else []:
            walk(top, [], None)
    except RecursionError as exc:
        raise ValueError("Layer annidati troppo in profondità.") from exc
    return {"version": root.get("version") or "1.3.0", "layers": layers}


def wms_layer_crs(layer: dict[str, Any], version: str) -> str | None:
    """CRS in cui GeoLibre web chiede il layer, ``None`` se non sa disegnarlo.

    Regola del plugin openrndt-geolibre (`crsOf`/`pickWmsCrs`): EPSG:3857 se
    c'è, altrimenti un CRS geografico (CRS:84 solo in WMS 1.3.0), altrimenti il
    primo ``EPSG:n``.
    """
    listed: list[str] = [str(c).upper() for c in layer.get("crs") or []]
    if any(c in {"EPSG:3857", "EPSG:900913"} for c in listed):
        return "EPSG:3857"
    v13 = version.startswith("1.3")
    for c in listed:
        if c in _GEOGRAPHIC_CRS and (c != "CRS:84" or v13):
            return c
    return next((c for c in listed if re.fullmatch(r"EPSG:\d+", c)), None)


def _fetch_bytes(url: str, timeout: float) -> bytes:
    """GET con la stessa validazione anti-SSRF di `check_resources`, anche a ogni redirect."""
    return _fetch(url, timeout)[0]


def _fetch(url: str, timeout: float, origin: str | None = None) -> tuple[bytes, httpx.Headers]:
    """Come `_fetch_bytes`, con le intestazioni della risposta finale; ``origin`` va nell'intestazione ``Origin``."""
    headers = {"User-Agent": USER_AGENT}
    if origin:
        headers["Origin"] = origin
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        blocked = _validate_check_url(current)
        if blocked is not None:
            raise ValueError(f"url-blocked:{blocked}")
        with httpx.stream(
            "GET", current, headers=headers, timeout=timeout, follow_redirects=False, verify=_PROBE_SSL_CONTEXT
        ) as response:
            if response.status_code in _REDIRECT_STATUSES and response.headers.get("location"):
                current = urljoin(current, response.headers["location"])
                continue
            if response.status_code >= 400:
                raise ValueError(f"HTTP {response.status_code}")
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > _MAX_CAPABILITIES_BYTES:
                    raise ValueError("risposta troppo grande")
            return bytes(body), response.headers
    raise ValueError("too-many-redirects")


def _cors_ok(headers: httpx.Headers) -> bool:
    """``Access-Control-Allow-Origin`` che lascia leggere la risposta a GeoLibre web."""
    return headers.get("access-control-allow-origin", "").strip() in {"*", GEOLIBRE_ORIGIN}


PROBE_TILE_SIZE = 64


def wms_probe_url(base: str, version: str, layer: str, bbox: list[float] | None) -> str:
    """GetMap di prova in EPSG:3857: 64x64 px, 4 km al centro di ``bbox`` (WGS84).

    Porting di `probeGetMapUrl`/`probeBbox3857` del plugin openrndt-geolibre:
    dice se il server disegna in EPSG:3857 un layer che non lo dichiara.
    """
    w, s, e, n = bbox or [12, 41.5, 13, 42.5]
    lon = (w + e) / 2
    lat = max(-85.0, min(85.0, (s + n) / 2))
    x = lon * _WORLD / 180
    y = math.log(math.tan(math.radians(90 + lat) / 2)) / (math.pi / 180) * (_WORLD / 180)
    half = 2000
    box = ",".join(f"{v:.2f}" for v in (x - half, y - half, x + half, y + half))
    v13 = version.startswith("1.3")
    params = [
        ("SERVICE", "WMS"),
        ("VERSION", "1.3.0" if v13 else "1.1.1"),
        ("REQUEST", "GetMap"),
        ("LAYERS", layer),
        ("STYLES", ""),
        ("CRS" if v13 else "SRS", "EPSG:3857"),
        ("BBOX", box),
        ("WIDTH", str(PROBE_TILE_SIZE)),
        ("HEIGHT", str(PROBE_TILE_SIZE)),
        ("FORMAT", "image/png"),
        ("TRANSPARENT", "true"),
    ]
    return f"{base}{'&' if urlparse(base).query else '?'}{urlencode(params, safe='/:,')}"


def _is_image(data: bytes) -> bool:
    """PNG, JPEG, GIF o WebP, dai primi byte (`isImage` del plugin)."""
    return (
        data[:4] == b"\x89PNG" or data[:2] == b"\xff\xd8" or data[:3] == b"GIF" or data[8:12] == b"WEBP"
    )


def wms_draws_3857(url: str, timeout: float) -> bool:
    """True se la GetMap di prova di :func:`wms_probe_url` dà a GeoLibre web una tile.

    Come `testTile` del plugin: un'immagine e, per un PNG, larga e alta 64 px
    (un'immagine fissa di altra misura, come quella del catasto dell'Agenzia
    delle Entrate, non vale; un PNG troncato prima della misura nemmeno, più
    severo del plugin). In più l'intestazione CORS, che nel plugin
    impone il browser stesso.
    """
    try:
        data, headers = _fetch(url, timeout, origin=GEOLIBRE_ORIGIN)
    except (httpx.HTTPError, ValueError):
        return False
    if not _cors_ok(headers) or not _is_image(data):
        return False
    if data[:4] == b"\x89PNG":
        # Un PNG senza IHDR completo (troncato) non è una tile che il browser sa mostrare.
        return len(data) >= 24 and int.from_bytes(data[16:20], "big") == PROBE_TILE_SIZE == int.from_bytes(data[20:24], "big")
    return True


def upgrade_to_https(target: str, fetched_from: str) -> str:
    """URL di operazione in `http://` riportato a https se le capabilities sono arrivate in https dallo stesso host.

    Porting di `upgradeToHttps` del plugin: i server passati a https tengono
    spesso i vecchi indirizzi (GeoWebCache del Veneto dichiara il GetTile in http).
    """
    t, f = urlparse(target), urlparse(fetched_from)
    if f.scheme == "https" and t.scheme == "http" and t.hostname and t.hostname == f.hostname:
        return urlunparse(t._replace(scheme="https"))
    return target


def preselected_name(url: str) -> str | None:
    """Layer nominato dall'URL (`LAYERS`, `LAYER`, `TYPENAME`, `TYPENAMES`), il primo se sono più d'uno."""
    for key, value in parse_qsl(urlparse(url).query, keep_blank_values=True):
        if key.lower() in {"layers", "layer", "typename", "typenames"} and value:
            return value.split(",")[0]
    return None


def _tokens(value: str) -> set[str]:
    plain = unicodedata.normalize("NFD", value.lower())
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return {t for t in re.split(r"[^a-z0-9]+", plain) if len(t) > 2}


def best_matching_layer(title: str, layers: list[dict[str, Any]]) -> str | None:
    """Layer il cui nome o titolo ha più parole in comune col titolo della scheda (`bestMatchingLayer` del plugin).

    ``None`` se nessun layer ha almeno una parola in comune.
    """
    wanted = _tokens(title)
    best: str | None = None
    best_score = 0
    for layer in layers:
        score = len(wanted & _tokens(f"{layer['name']} {layer.get('title') or ''}"))
        if score > best_score:
            best, best_score = layer["name"], score
    return best


def _services_of(resources: list[dict[str, str]], kind: str) -> list[str]:
    """Un servizio per base URL (lo schema non conta), nell'ordine della scheda; https se dichiarato in entrambi."""
    services: dict[str, str] = {}
    for resource in resources:
        if resource.get("type") != kind or not re.match(r"https?://", resource["url"], re.IGNORECASE):
            continue
        url = resource["url"]
        base = url if kind == "WMTS" and urlparse(url).path.lower().endswith(".xml") else service_base_url(url)
        key = re.sub(r"^https?://", "", base, flags=re.IGNORECASE).lower()
        if key not in services or (base.lower().startswith("https://") and services[key].lower().startswith("http://")):
            services[key] = base
    return list(services.values())


_HTTP_NOTE = "servizio in http://: GeoLibre web (https) potrebbe non mostrarlo"
_WMTS_REASONS = {
    "no-web-mercator": "non offerto in una griglia Web Mercator (solo {systems}): GeoLibre non sa disegnarlo",
    "matrix-ids": "griglia Web Mercator con livelli che GeoLibre non sa indirizzare (id non numerati per zoom)",
    "template": "l'indirizzo delle tile chiede valori che GeoLibre non sa riempire (tempo o altre dimensioni)",
}


def list_layers(
    item_id: str,
    resources: list[dict[str, str]],
    *,
    timeout: float | None = None,
    title: str | None = None,
) -> list[dict[str, Any]]:
    """Layer con nome dei servizi WMS e WMTS di una scheda, ognuno con un `geolibre_url`.

    Un servizio per base URL (lo schema non conta), nell'ordine della scheda,
    prima i WMS poi i WMTS. Ogni riga: ``service``, ``kind`` (``wms``/``wmts``),
    ``name``, ``title``, ``crs`` (quello in cui GeoLibre lo chiederebbe),
    ``tile_url`` (WMTS: il template ``{z}/{x}/{y}``), ``cors`` (se GeoLibre web
    può leggere il servizio: WMS dal GetCapabilities, WMTS da una tile per
    servizio; senza CORS niente ``geolibre_url``),
    ``geolibre_url`` (apre GeoLibre web col layer sulla mappa), ``note`` ed
    ``error``. Un servizio che non risponde dà una riga con ``name`` ``None``
    ed ``error``. Come il plugin, un nome già visto in un servizio precedente
    si risolve su quello: ``geolibre_url`` ``None`` e una nota. ``title`` (il
    titolo della scheda) sceglie il layer su cui provare il CORS, come il plugin.
    Un WMS con CORS in cui un layer non dichiara EPSG:3857 riceve una GetMap
    di prova in EPSG:3857 (:func:`wms_probe_url`): se il server la disegna,
    tutti i suoi layer valgono come EPSG:3857, come nel plugin.
    """
    from openrndt.search import geolibre_url

    if timeout is None:
        timeout = get_timeout()
    empty: dict[str, Any] = {
        "service": None, "kind": None, "name": None, "title": None, "crs": None,
        "tile_url": None, "cors": None, "geolibre_url": None, "note": None, "error": None,
    }
    rows: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for base in _services_of(resources, "WMS"):
        row_base = {**empty, "service": base, "kind": "wms"}
        try:
            data, headers = _fetch(capabilities_url(base), timeout, origin=GEOLIBRE_ORIGIN)
            caps = parse_wms_capabilities(data)
        except (httpx.HTTPError, ValueError) as exc:
            rows.append({**row_base, "error": str(exc) or type(exc).__name__})
            continue
        # GeoLibre web legge capabilities e tile col fetch del browser: senza CORS non aggiunge nulla.
        cors = _cors_ok(headers)
        row_base["cors"] = cors
        # Come il plugin (`prepareWms`): una GetMap di prova in EPSG:3857 se un layer non lo
        # dichiara; molti server (ArcGIS, GeoServer con elenco ristretto) lo disegnano lo stesso.
        undeclared = [layer for layer in caps["layers"] if wms_layer_crs(layer, caps["version"]) != "EPSG:3857"]
        draws_3857 = False
        if cors and undeclared:
            sample = next(
                (layer for layer in undeclared if not layer["group"] and layer["bbox"]),
                next((layer for layer in undeclared if layer["bbox"]), undeclared[0]),
            )
            draws_3857 = wms_draws_3857(
                wms_probe_url(base, caps["version"], sample["name"], sample["bbox"]), timeout
            )
        http_note = _HTTP_NOTE if base.lower().startswith("http://") else None
        for layer in caps["layers"]:
            name = layer["name"]
            row = {**row_base, "name": name, "title": layer["title"], "note": http_note}
            if name in seen_names:
                row["note"] = "nome già in un servizio precedente della scheda: GeoLibre usa quello"
            else:
                seen_names.add(name)
                crs = wms_layer_crs(layer, caps["version"])
                if crs != "EPSG:3857" and draws_3857:
                    crs = "EPSG:3857"
                    row["note"] = "; ".join(
                        n for n in (http_note, "EPSG:3857 non dichiarato, ma il server lo disegna (GetMap di prova)") if n
                    )
                row["crs"] = crs
                if crs is None:
                    row["note"] = "nessun CRS che GeoLibre sa disegnare"
                elif not cors:
                    row["note"] = "il servizio non ha l'intestazione CORS: GeoLibre web non può leggerlo"
                else:
                    row["geolibre_url"] = geolibre_url(item_id, [("wms", name)])
            rows.append(row)
    hints = [h for h in (preselected_name(r["url"]) for r in resources if r.get("type") == "WMTS") if h]
    for base in _services_of(resources, "WMTS"):
        rows.extend(_wmts_rows(item_id, base, {**empty, "service": base, "kind": "wmts"}, seen_names, hints, title, timeout))
    return rows


def _wmts_rows(
    item_id: str,
    base: str,
    row_base: dict[str, Any],
    seen_names: set[str],
    hints: list[str],
    title: str | None,
    timeout: float,
) -> list[dict[str, Any]]:
    from openrndt.search import geolibre_url

    caps_url = wmts_capabilities_url(base)
    try:
        caps = parse_wmts_capabilities(_fetch_bytes(caps_url, timeout))
    except (httpx.HTTPError, ValueError) as exc:
        return [{**row_base, "error": str(exc) or type(exc).__name__}]
    if caps["get_tile_url"]:
        caps["get_tile_url"] = upgrade_to_https(caps["get_tile_url"], caps_url)
    for layer in caps["layers"]:
        for t in layer["templates"]:
            t["template"] = upgrade_to_https(t["template"], caps_url)
    try:
        plans = {layer["name"]: plan_wmts_layer(caps, layer) for layer in caps["layers"]}
    except (ValueError, ArithmeticError) as exc:
        # Capabilities con valori che il piano non regge: errore del servizio, non di `get`.
        return [{**row_base, "error": f"capabilities WMTS non utilizzabili: {exc}"}]
    addable = [layer for layer in caps["layers"] if plans[layer["name"]]["ok"]]
    # Una tile del layer voluto (o del primo disegnabile), come la chiederebbe il browser.
    cors: bool | None = None
    cors_error: str | None = None
    if addable:
        wanted = next((h for h in hints if h in plans), None) or best_matching_layer(title or "", addable)
        sample = next((layer for layer in addable if layer["name"] == wanted), addable[0])
        plan = plans[sample["name"]]
        probe = wmts_probe_url(plan["template"], sample["bbox"], plan["minzoom"], plan["maxzoom"])
        cors, cors_error = tile_cors(probe, timeout)
    http_note = _HTTP_NOTE if base.lower().startswith("http://") else None
    rows: list[dict[str, Any]] = []
    for layer in caps["layers"]:
        name = layer["name"]
        plan = plans[name]
        row = {**row_base, "name": name, "title": layer["title"], "note": http_note}
        if name in seen_names:
            row["note"] = "nome già in un servizio precedente della scheda: GeoLibre usa quello"
        elif not plan["ok"]:
            seen_names.add(name)
            row["note"] = _WMTS_REASONS[plan["reason"]].format(systems=", ".join(plan["systems"][:6]) or "?")
        else:
            seen_names.add(name)
            row["crs"] = "EPSG:3857"
            row["tile_url"] = plan["template"]
            row["cors"] = cors
            if cors:
                row["geolibre_url"] = geolibre_url(item_id, [("wmts", name)])
            elif cors is False:
                row["note"] = "le tile non hanno l'intestazione CORS: GeoLibre web non può mostrarle"
            else:
                row["note"] = f"la tile di prova non risponde ({cors_error})"
        rows.append(row)
    return rows


# --- layer dei servizi WMTS ---------------------------------------------------
# Porting di `src/rndt/wmts.ts` del plugin openrndt-geolibre (0.5.0): GeoLibre
# web disegna un WMTS solo da un template `{z}/{x}/{y}`, quindi solo in una
# griglia Web Mercator con tile da 256 px e id delle matrici "prefisso + zoom".

GEOLIBRE_ORIGIN = "https://web.geolibre.app"
_ZOOM0_SCALE = 559082264.0287178
_WORLD = 20037508.342789244
_WEB_MERCATOR_RE = re.compile(r"(?:^|[:/])(3857|900913|102100|102113|3785)$")
_URN_EPSG_RE = re.compile(r"^urn:ogc:def:crs:EPSG:(?:[\d.]*:)?", re.IGNORECASE)


def wmts_capabilities_url(url: str) -> str:
    """GetCapabilities WMTS: un documento statico `…/WMTSCapabilities.xml` si legge com'è."""
    if urlparse(url).path.lower().endswith(".xml"):
        return url
    base = service_base_url(url)
    return f"{base}{'&' if urlparse(base).query else '?'}SERVICE=WMTS&REQUEST=GetCapabilities"


def _numbers(value: str) -> list[float]:
    try:
        return [float(v) for v in value.split()]
    except ValueError:
        return []


def parse_wmts_capabilities(xml: str | bytes) -> dict[str, Any]:
    """Layer, tile matrix set ed endpoint GetTile KVP di una GetCapabilities WMTS.

    ``layers``: ``name`` (Identifier), ``title``, ``bbox`` in gradi, ``style``
    (quello di default, altrimenti il primo), ``formats``, ``links``
    (``{"set", "limits"}``) e ``templates`` RESTful (``{"format", "template"}``).
    ``sets``: per id, ``crs``, ``well_known`` e ``matrices``. ``get_tile_url``:
    l'endpoint KVP senza ``?`` finale, o ``None``. Solleva ``ValueError`` su
    XML non valido, su un'eccezione OGC o su un documento che non è WMTS.
    """
    raw = xml.encode("utf-8") if isinstance(xml, str) else xml
    try:
        root = ET.fromstring(_strip_doctype(raw))
    except ET.ParseError as exc:
        raise ValueError("Il servizio non ha restituito XML valido.") from exc
    if _local(root.tag) in {"ServiceExceptionReport", "ExceptionReport"}:
        message = " ".join("".join(root.itertext()).split())
        raise ValueError(f"Errore del servizio: {message[:300]}")
    if _local(root.tag) != "Capabilities":
        raise ValueError("Il documento non è una GetCapabilities WMTS.")
    contents = next((el for el in root.iter() if _local(el.tag) == "Contents"), None)

    sets: dict[str, dict[str, Any]] = {}
    for el in _children(contents, "TileMatrixSet") if contents is not None else []:
        set_id = _text(_child(el, "Identifier"))
        if not set_id:
            continue
        matrices = []
        for m in _children(el, "TileMatrix"):
            corner = _numbers(_text(_child(m, "TopLeftCorner")))
            try:
                scale = float(_text(_child(m, "ScaleDenominator")))
                width = int(float(_text(_child(m, "TileWidth"))))
                height = int(float(_text(_child(m, "TileHeight"))))
            except ValueError:
                scale, width, height = 0.0, 0, 0
            matrices.append(
                {
                    "id": _text(_child(m, "Identifier")),
                    "scale": scale,
                    "top_left": corner[:2] if len(corner) >= 2 else None,
                    "tile_width": width,
                    "tile_height": height,
                }
            )
        sets[set_id] = {
            "id": set_id,
            "crs": _text(_child(el, "SupportedCRS")),
            "well_known": _text(_child(el, "WellKnownScaleSet")),
            "matrices": matrices,
        }

    layers: list[dict[str, Any]] = []
    for el in _children(contents, "Layer") if contents is not None else []:
        name = _text(_child(el, "Identifier"))
        if not name:
            continue
        box = _child(el, "WGS84BoundingBox")
        lower = _numbers(_text(_child(box, "LowerCorner"))) if box is not None else []
        upper = _numbers(_text(_child(box, "UpperCorner"))) if box is not None else []
        bbox = lower[:2] + upper[:2] if len(lower) >= 2 and len(upper) >= 2 else None
        styles = _children(el, "Style")
        style_el = next((s for s in styles if s.get("isDefault") == "true"), styles[0] if styles else None)
        links = []
        for link in _children(el, "TileMatrixSetLink"):
            limits = _child(link, "TileMatrixSetLimits")
            links.append(
                {
                    "set": _text(_child(link, "TileMatrixSet")),
                    "limits": (
                        [_text(_child(lim, "TileMatrix")) for lim in _children(limits, "TileMatrixLimits")]
                        if limits is not None
                        else None
                    ),
                }
            )
        templates = [
            {"format": r.get("format") or "", "template": r.get("template") or ""}
            for r in _children(el, "ResourceURL")
            if (r.get("resourceType") or "tile") == "tile" and r.get("template")
        ]
        layers.append(
            {
                "name": name,
                "title": _text(_child(el, "Title")) or name,
                "bbox": bbox,
                "style": _text(_child(style_el, "Identifier")) if style_el is not None else "default",
                "formats": [f for f in (_text(x) for x in _children(el, "Format")) if f],
                "links": links,
                "templates": templates,
            }
        )

    get_tile = next(
        (op for op in root.iter() if _local(op.tag) == "Operation" and op.get("name") == "GetTile"), None
    )
    get_el = next((g for g in get_tile.iter() if _local(g.tag) == "Get"), None) if get_tile is not None else None
    href = ""
    if get_el is not None:
        href = next((v for k, v in get_el.attrib.items() if _local(k) == "href"), "")
    get_tile_url = re.sub(r"[?&]+$", "", href) or None
    return {"get_tile_url": get_tile_url, "sets": sets, "layers": layers}


def web_mercator_zooms(matrix_set: dict[str, Any]) -> tuple[str, dict[str, int]] | str | None:
    """Zoom di ogni matrice di una griglia Web Mercator e prefisso degli id.

    ``None`` se la griglia non è Web Mercator a 256 px dall'angolo del mondo;
    ``"matrix-ids"`` se lo è ma gli id non sono "prefisso + zoom" (zero-padded
    come `00` di MapProxy a Bolzano, o con nomi): GeoLibre non sa riempirli.
    """
    if not _WEB_MERCATOR_RE.search(matrix_set["crs"].strip()) or not matrix_set["matrices"]:
        return None
    zooms: dict[str, int] = {}
    for m in matrix_set["matrices"]:
        if m["tile_width"] != 256 or m["tile_height"] != 256 or not m["top_left"]:
            return None
        # `float()` accetta "NaN" e "inf": un server che li scrive non ha una griglia usabile.
        if not all(math.isfinite(v) for v in (m["scale"], *m["top_left"])) or m["scale"] <= 0:
            return None
        # I server arrotondano l'angolo in modo diverso (GeoWebCache: -2.003750834E7 2.0037508E7).
        if abs(m["top_left"][0] + _WORLD) > 1 or abs(m["top_left"][1] - _WORLD) > 1:
            return None
        z = round(math.log2(_ZOOM0_SCALE / m["scale"]))
        if not 0 <= z <= 30 or abs(m["scale"] * 2**z / _ZOOM0_SCALE - 1) > 0.01:
            return None
        zooms[m["id"]] = z
    first, first_zoom = next(iter(zooms.items()))
    if not first.endswith(str(first_zoom)):
        return "matrix-ids"
    prefix = first[: len(first) - len(str(first_zoom))]
    if prefix[-1:].isdigit():
        return "matrix-ids"
    if any(i != f"{prefix}{z}" for i, z in zooms.items()):
        return "matrix-ids"
    return prefix, zooms


def _pick_format(formats: list[str]) -> str:
    return (
        next((f for f in formats if re.search("png", f, re.I)), None)
        or next((f for f in formats if re.search("jpe?g", f, re.I)), None)
        or (formats[0] if formats else "image/png")
    )


def _tile_template(caps: dict[str, Any], layer: dict[str, Any], set_id: str, prefix: str, fmt: str) -> str | None:
    rest = next((t for t in layer["templates"] if t["format"] == fmt), None) or (
        layer["templates"][0] if layer["templates"] else None
    )
    if rest:
        filled = rest["template"]
        for pattern, value in (
            (r"\{Style\}", quote(layer["style"], safe="")),
            (r"\{TileMatrixSet\}", quote(set_id, safe="")),
            (r"\{TileMatrix\}", f"{quote(prefix, safe='')}{{z}}"),
            (r"\{TileRow\}", "{y}"),
            (r"\{TileCol\}", "{x}"),
        ):
            filled = re.sub(pattern, value.replace("\\", "\\\\"), filled, flags=re.IGNORECASE)
        return None if re.search(r"\{(?![zxy]\})[^}]*\}", filled) else filled
    if not caps["get_tile_url"]:
        return None
    params = [
        "SERVICE=WMTS",
        "REQUEST=GetTile",
        "VERSION=1.0.0",
        f"LAYER={quote(layer['name'], safe='')}",
        f"STYLE={quote(layer['style'], safe='')}",
        f"TILEMATRIXSET={quote(set_id, safe='')}",
        f"TILEMATRIX={quote(prefix, safe='')}{{z}}",
        "TILEROW={y}",
        "TILECOL={x}",
        f"FORMAT={quote(fmt, safe='')}",
    ]
    base = caps["get_tile_url"]
    return f"{base}{'&' if '?' in base else '?'}{'&'.join(params)}"


def _is_google_maps(matrix_set: dict[str, Any]) -> bool:
    return bool(re.search("GoogleMapsCompatible", matrix_set["well_known"] + " " + matrix_set["id"], re.I))


def plan_wmts_layer(caps: dict[str, Any], layer: dict[str, Any]) -> dict[str, Any]:
    """Come GeoLibre aggiungerebbe il layer: griglia, template `{z}/{x}/{y}` e zoom.

    ``{"ok": True, "set", "template", "minzoom", "maxzoom", "format"}``, oppure
    ``{"ok": False, "reason", "systems"}`` con ``reason`` fra ``no-web-mercator``,
    ``matrix-ids`` e ``template``, e i sistemi in cui il layer è offerto.
    """
    linked = [(link, caps["sets"][link["set"]]) for link in layer["links"] if link["set"] in caps["sets"]]
    systems = list(dict.fromkeys(_URN_EPSG_RE.sub("EPSG:", s["crs"]) for _, s in linked))
    reason = "no-web-mercator"
    candidates = []
    for link, matrix_set in linked:
        mercator = web_mercator_zooms(matrix_set)
        if mercator == "matrix-ids":
            reason = "matrix-ids"
        elif isinstance(mercator, tuple):
            candidates.append((link, matrix_set, mercator))
    candidates.sort(key=lambda c: not _is_google_maps(c[1]))
    for link, matrix_set, (prefix, zooms) in candidates:
        ids = link["limits"] if link["limits"] is not None else [m["id"] for m in matrix_set["matrices"]]
        covered = [zooms[i] for i in ids if i in zooms]
        if not covered:
            continue
        fmt = _pick_format(layer["formats"] or [t["format"] for t in layer["templates"]])
        template = _tile_template(caps, layer, matrix_set["id"], prefix, fmt)
        if not template:
            reason = "template"
            continue
        return {"ok": True, "set": matrix_set["id"], "template": template, "minzoom": min(covered), "maxzoom": max(covered), "format": fmt}
    return {"ok": False, "reason": reason, "systems": systems}


def wmts_probe_url(template: str, bbox: list[float] | None, minzoom: int, maxzoom: int) -> str:
    """Una tile del template per provare il servizio: al centro dell'estensione, dove la coprono poche tile."""
    w, s, e, n = bbox or [6.6, 36.6, 18.5, 47.1]
    lon = (w + e) / 2
    lat = max(-85.0, min(85.0, (s + n) / 2))
    span = max(e - w, n - s, 1e-6)
    z = max(minzoom, min(maxzoom, math.floor(math.log2(360 / span)) + 2))
    count = 2**z
    x = min(count - 1, math.floor((lon + 180) / 360 * count))
    rad = math.radians(lat)
    y = min(count - 1, math.floor((1 - math.log(math.tan(rad) + 1 / math.cos(rad)) / math.pi) / 2 * count))
    return template.replace("{z}", str(z), 1).replace("{x}", str(x), 1).replace("{y}", str(y), 1)


def tile_cors(url: str, timeout: float) -> tuple[bool | None, str | None]:
    """GET di una tile con ``Origin`` di GeoLibre web: ``(cors, errore)``.

    Segue fino a `_MAX_REDIRECTS` redirect, validando ogni destinazione come
    `check_resources`, e legge l'intestazione dalla risposta finale. ``cors`` è
    True se ``Access-Control-Allow-Origin`` è ``*`` o l'origine di GeoLibre,
    False se manca, ``None`` se la tile non risponde (con l'errore).
    """
    headers = {"User-Agent": USER_AGENT, "Origin": GEOLIBRE_ORIGIN}
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        blocked = _validate_check_url(current)
        if blocked is not None:
            return None, f"url-blocked:{blocked}"
        try:
            with httpx.stream(
                "GET", current, headers=headers, timeout=timeout, follow_redirects=False, verify=_PROBE_SSL_CONTEXT
            ) as r:
                if r.status_code in _REDIRECT_STATUSES and r.headers.get("location"):
                    current = urljoin(current, r.headers["location"])
                    continue
                if r.status_code >= 400:
                    return None, f"tile HTTP {r.status_code}"
                allow = r.headers.get("access-control-allow-origin", "").strip()
                return allow in {"*", GEOLIBRE_ORIGIN}, None
        except httpx.HTTPError as exc:
            return None, f"tile: {type(exc).__name__}"
    return None, "tile: too-many-redirects"


def pick_map_layer(
    rows: list[dict[str, Any]], resources: list[dict[str, str]], *, title: str | None = None, record_type: str | None = None
) -> dict[str, Any] | None:
    """Il layer da mettere sulla mappa di GeoLibre web, fra le righe di :func:`list_layers`.

    Candidati: le righe con ``geolibre_url`` che GeoLibre web disegna, cioè i
    WMTS (già verificati: griglia Web Mercator e CORS) e i WMS https con CORS
    offerti in EPSG:3857, dichiarato o disegnato nella GetMap di prova. Scelta come il plugin (`wantedLayer`): il layer nominato da un
    link della scheda (`LAYERS=`…), altrimenti l'unico candidato, altrimenti
    quello col titolo più vicino a quello della scheda; per una scheda di tipo
    ``service`` nessuna scelta per titolo. ``None`` se non c'è un candidato sicuro.
    """
    candidates = [
        r
        for r in rows
        if r.get("geolibre_url")
        and (r["kind"] == "wmts" or (r["crs"] == "EPSG:3857" and str(r["service"]).lower().startswith("https://")))
    ]
    if not candidates:
        return None
    hints = [h for h in (preselected_name(r["url"]) for r in resources) if h]
    for hint in hints:
        hit = next((r for r in candidates if r["name"] == hint), None)
        if hit:
            return hit
    if len(candidates) == 1:
        return candidates[0]
    if record_type == "service":
        return None
    name = best_matching_layer(title or "", candidates)
    return next((r for r in candidates if r["name"] == name), None)


def geolibre_map_url(item_payload: dict[str, Any], *, timeout: float | None = None) -> str | None:
    """Indirizzo che apre GeoLibre web con il layer della scheda già sulla mappa.

    Legge le capabilities dei WMS e WMTS della scheda (vedi :func:`list_layers`)
    e sceglie il layer con :func:`pick_map_layer`. ``item_payload`` è la busta
    di :func:`openrndt.item.get_item`. ``None`` se nessun layer è disegnabile
    in GeoLibre web o la scelta non è sicura.
    """
    source = item_payload.get("_source") or {}
    item_id = item_payload.get("_id") or source.get("fileid")
    if not item_id:
        return None
    title = source.get("title")
    record_type = source.get("apiso_Type_s")
    resources = extract_resources(item_payload)
    rows = list_layers(
        str(item_id), resources, timeout=timeout, title=title if isinstance(title, str) else None
    )
    picked = pick_map_layer(
        rows,
        resources,
        title=title if isinstance(title, str) else None,
        record_type=record_type if isinstance(record_type, str) else None,
    )
    return picked["geolibre_url"] if picked else None
