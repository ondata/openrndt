"""Estrazione e verifica rapida delle risorse fruibili di un metadato RNDT."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

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
        kind = str(kind_raw).upper() if isinstance(kind_raw, str) and kind_raw else _infer_kind(href)
        if kind == "LINK":
            continue
        if href in seen:
            continue
        seen.add(href)
        rows.append({"type": kind, "url": href, "source": "links"})

    for key in ("webServices_s", "links_s"):
        for url in _normalize_url_values(source.get(key)):
            kind = _infer_kind(url)
            if kind == "link":
                continue
            if url in seen:
                continue
            seen.add(url)
            rows.append({"type": kind, "url": url, "source": key})
    return rows


def check_resources(resources: list[dict[str, str]], *, timeout: float | None = None) -> list[dict[str, Any]]:
    """Controlla raggiungibilità endpoint risorsa con GET e timeout breve."""
    if timeout is None:
        timeout = get_timeout()

    checked: list[dict[str, Any]] = []
    headers = {"User-Agent": USER_AGENT}
    for resource in resources:
        row: dict[str, Any] = dict(resource)
        try:
            response = httpx.get(
                resource["url"],
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
            )
            row["status_code"] = response.status_code
            row["ok"] = 200 <= response.status_code < 400
            row["final_url"] = str(response.url)
        except httpx.HTTPError as exc:
            row["status_code"] = None
            row["ok"] = False
            row["final_url"] = resource["url"]
            row["error"] = type(exc).__name__
        checked.append(row)
    return checked
