"""Estrazione e verifica rapida delle risorse fruibili di un metadato RNDT."""

from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx

from openrndt.client import USER_AGENT
from openrndt.config import get_timeout

_NON_RESOURCE_RELS = {"alternate", "icon", "self"}
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
    return None


def _blocked_resolved_hostname_reason(hostname: str) -> str | None:
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return None
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


def check_resources(resources: list[dict[str, str]], *, timeout: float | None = None) -> list[dict[str, Any]]:
    """Controlla raggiungibilità endpoint con probe leggero (HEAD, fallback GET)."""
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
        blocked_reason = _validate_check_url(resource["url"])
        if blocked_reason is not None:
            row["error"] = f"url-blocked:{blocked_reason}"
            checked.append(row)
            continue
        try:
            response = httpx.head(
                resource["url"],
                headers=headers,
                timeout=timeout,
                follow_redirects=False,
            )
            location = response.headers.get("location")
            if location:
                row["redirect_url"] = urljoin(resource["url"], location)
            # Alcuni endpoint non supportano HEAD: fallback a GET in streaming.
            if response.status_code in {405, 501}:
                with httpx.stream(
                    "GET",
                    resource["url"],
                    headers=headers,
                    timeout=timeout,
                    follow_redirects=False,
                ) as stream_response:
                    location = stream_response.headers.get("location")
                    if location:
                        row["redirect_url"] = urljoin(resource["url"], location)
                    row["status_code"] = stream_response.status_code
                    row["ok"] = 200 <= stream_response.status_code < 400
                    row["final_url"] = str(stream_response.url)
                    row["method"] = "GET"
                checked.append(row)
                continue
            row["status_code"] = response.status_code
            row["ok"] = 200 <= response.status_code < 400
            row["final_url"] = str(response.url)
        except httpx.HTTPError as exc:
            row["error"] = type(exc).__name__
        checked.append(row)
    return checked
