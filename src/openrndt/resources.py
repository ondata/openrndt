"""Estrazione e verifica rapida delle risorse fruibili di un metadato RNDT."""

from __future__ import annotations

import ipaddress
import socket
import ssl
import time
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

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
    """Estrae e deduplica risorse utili (WMS/WFS/.../download) dal payload item."""
    source = item_payload.get("_source") or {}
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

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
