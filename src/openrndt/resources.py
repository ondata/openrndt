"""Estrazione e verifica rapida delle risorse fruibili di un metadato RNDT."""

from __future__ import annotations

import ipaddress
import re
import socket
import ssl
import time
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import parse_qs, parse_qsl, urlencode, urljoin, urlparse, urlunparse

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
        if kind == "link":
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
        text = raw.decode(declared.group(1).decode() if declared else "utf-8", errors="replace")
        try:
            root = ET.fromstring(_repair_xml(text).encode("utf-8"))
        except ET.ParseError as exc:
            raise ValueError("Il servizio non ha restituito XML valido.") from exc
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
    for top in _children(capability, "Layer") if capability is not None else []:
        walk(top, [], None)
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
    headers = {"User-Agent": USER_AGENT}
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
            return bytes(body)
    raise ValueError("too-many-redirects")


def list_layers(
    item_id: str, resources: list[dict[str, str]], *, timeout: float | None = None
) -> list[dict[str, Any]]:
    """Layer con nome dei servizi WMS di una scheda, ognuno con un `geolibre_url`.

    Un servizio per base URL (lo schema non conta), nell'ordine della scheda.
    Ogni riga: ``service``, ``name``, ``title``, ``crs`` (quello in cui GeoLibre
    lo chiederebbe), ``geolibre_url`` (apre GeoLibre web col layer sulla mappa),
    ``note`` ed ``error``. Un servizio che non risponde dà una riga con
    ``name`` ``None`` ed ``error``. Come il plugin, un nome già visto in un
    servizio precedente si risolve su quello: ``geolibre_url`` ``None`` e una nota.
    """
    from openrndt.search import geolibre_url

    if timeout is None:
        timeout = get_timeout()
    # Un servizio per base URL, nell'ordine della scheda; se la scheda lo
    # dichiara sia in http sia in https, si usa https.
    services: dict[str, str] = {}
    for resource in resources:
        if resource.get("type") != "WMS" or not re.match(r"https?://", resource["url"], re.IGNORECASE):
            continue
        base = service_base_url(resource["url"])
        key = re.sub(r"^https?://", "", base, flags=re.IGNORECASE).lower()
        if key not in services or (base.lower().startswith("https://") and services[key].lower().startswith("http://")):
            services[key] = base
    rows: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for base in services.values():
        row_base: dict[str, Any] = {"service": base, "name": None, "title": None, "crs": None, "geolibre_url": None, "note": None, "error": None}
        try:
            caps = parse_wms_capabilities(_fetch_bytes(capabilities_url(base), timeout))
        except (httpx.HTTPError, ValueError) as exc:
            rows.append({**row_base, "error": str(exc) or type(exc).__name__})
            continue
        http_note = "servizio in http://: GeoLibre web (https) potrebbe non mostrarlo" if base.lower().startswith("http://") else None
        for layer in caps["layers"]:
            name = layer["name"]
            row = {**row_base, "name": name, "title": layer["title"], "note": http_note}
            if name in seen_names:
                row["note"] = "nome già in un servizio precedente della scheda: GeoLibre usa quello"
            else:
                seen_names.add(name)
                crs = wms_layer_crs(layer, caps["version"])
                row["crs"] = crs
                if crs is None:
                    row["note"] = "nessun CRS che GeoLibre sa disegnare"
                else:
                    row["geolibre_url"] = geolibre_url(item_id, [("wms", name)])
            rows.append(row)
    return rows
