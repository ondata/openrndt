"""Chiamata e parsing di /rest/metadata/search."""

from __future__ import annotations

import re
from typing import Any, cast

from openrndt.client import rndt_request
from openrndt.codelists import DATA_CATEGORIES

SEARCH_PATH = "/rest/metadata/search"
MAX_NUM = 5000

# Link `rel` che NON sono risorse fruibili (rappresentazioni del metadato stesso).
_NON_RESOURCE_RELS = {"alternate", "icon", "self"}
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _build_category_clause(values: str) -> str:
    """Traduce una lista di categorie ISO 19115 in clausola Lucene su `keywords_s`.

    Sul RNDT il parametro query string `dataCategory` non filtra: il filtro vero
    è `q=keywords_s:VAL`. Le categorie multiple sono separate da virgola.
    """
    items = [v.strip() for v in values.split(",") if v.strip()]
    if not items:
        return ""
    if len(items) == 1:
        return f"keywords_s:{items[0]}"
    joined = " OR ".join(items)
    return f"keywords_s:({joined})"


def _normalize_bbox_crs(bbox_crs: str | None) -> str | None:
    if bbox_crs is None:
        return None
    norm = bbox_crs.strip().upper().replace(":", "")
    if norm in {"EPSG4326", "CRS84", "WGS84"}:
        return "EPSG:4326"
    raise ValueError(
        "`bbox_crs` non supportato: usare EPSG:4326 (alias accettati: CRS:84, WGS84)."
    )


def _validate_iso_date(value: str, *, param_name: str) -> None:
    if not _ISO_DATE_RE.match(value):
        raise ValueError(f"`{param_name}` deve essere nel formato yyyy-mm-dd.")


def _build_date_range_clause(field: str, start: str | None, end: str | None, *, label: str) -> str | None:
    if start is None and end is None:
        return None
    if start is not None:
        _validate_iso_date(start, param_name=f"{label}_from")
    if end is not None:
        _validate_iso_date(end, param_name=f"{label}_to")
    lower = f"{start}T00:00:00Z" if start is not None else "*"
    upper = f"{end}T23:59:59Z" if end is not None else "*"
    return f"{field}:[{lower} TO {upper}]"


def search(
    *,
    q: str | None = None,
    bbox: str | None = None,
    bbox_crs: str | None = None,
    data_category: str | None = None,
    time: str | None = None,
    modified: str | None = None,
    updated_from: str | None = None,
    updated_to: str | None = None,
    published_from: str | None = None,
    published_to: str | None = None,
    sort: str | None = None,
    start: int = 1,
    num: int = 10,
    fmt: str = "json",
    item_id: str | None = None,
) -> dict[str, Any] | str:
    """Esegue una ricerca su /rest/metadata/search.

    Ritorna un dict (parsed JSON) se `fmt` è `json` o `json-source`,
    altrimenti la stringa con il body grezzo (XML, CSV, KML, …).

    Nota su `sort` (verificato live): l'ordinamento reale usa la sintassi
    `campo:asc|desc` su un campo sortable (keyword `_s`, data `_dt`, intero `_i`),
    es. ``sort="apiso_Modified_dt:desc"``. I valori ``dateDescending`` /
    ``dateAscending`` documentati ufficialmente NON ordinano (vengono ignorati).
    Non esiste un campo data-di-pubblicazione ordinabile: il proxy più affidabile
    per "ultimi pubblicati" è ``apiso_Modified_dt``.

    Solleva ``ValueError`` su parametri non validi e ``httpx.HTTPError`` (incluse
    ``httpx.HTTPStatusError`` per le risposte 4xx/5xx e ``httpx.ConnectError`` /
    ``httpx.TimeoutException`` per i problemi di rete) se la richiesta fallisce.
    Con ``fmt`` JSON, una risposta con body non-JSON valido (pur status 2xx)
    solleva ``json.JSONDecodeError`` (sottoclasse di ``ValueError``).
    """
    if num > MAX_NUM:
        raise ValueError(f"`num` non può superare {MAX_NUM} (richiesto: {num}).")
    if start < 1:
        raise ValueError("`start` deve essere ≥ 1.")
    if bbox_crs is not None and bbox is None:
        raise ValueError("`bbox_crs` richiede anche `bbox`.")
    if bbox is not None:
        _normalize_bbox_crs(bbox_crs)
    if modified is not None and (updated_from is not None or updated_to is not None):
        raise ValueError("Usa `modified` oppure `updated_from/updated_to`, non entrambi.")

    params: dict[str, Any] = {"f": fmt, "start": start, "num": num}
    q_parts: list[str] = []
    if q:
        q_parts.append(f"({q})" if data_category else q)
    if data_category:
        clause = _build_category_clause(data_category)
        if clause:
            q_parts.append(clause)
    updated_clause = _build_date_range_clause("apiso_Modified_dt", updated_from, updated_to, label="updated")
    if updated_clause:
        q_parts.append(updated_clause)
    published_clause = _build_date_range_clause(
        "apiso_PublicationDate_dt", published_from, published_to, label="published"
    )
    if published_clause:
        q_parts.append(published_clause)
    if q_parts:
        params["q"] = " AND ".join(q_parts) if len(q_parts) > 1 else q_parts[0]
    if bbox:
        params["bbox"] = bbox
    if time:
        params["time"] = time
    if modified:
        params["modified"] = modified
    if sort:
        params["sort"] = sort
    if item_id:
        params["id"] = item_id

    response = rndt_request(SEARCH_PATH, params=params)
    response.raise_for_status()
    if fmt in {"json", "json-source"}:
        data: dict[str, Any] = response.json()
        return data
    return response.text


def _resource_types(links: list[dict[str, Any]]) -> list[str]:
    """Tipi di risorsa fruibile (WMS/WFS/download/…) dedotti dai `links`.

    Esclude le rappresentazioni del metadato (rel alternate/icon/self) e tiene i
    `dctype` valorizzati; un `rel=enclosure` senza dctype è un download diretto.
    """
    types: set[str] = set()
    for link in links:
        if link.get("rel") in _NON_RESOURCE_RELS:
            continue
        dctype = link.get("dctype")
        if dctype:
            types.add(dctype)
        elif link.get("rel") == "enclosure":
            types.add("download")
    return sorted(types)


def _topic_category(source: dict[str, Any], categories: list[dict[str, Any]]) -> str | None:
    """Categoria ISO 19115 del record.

    Preferisce `apiso_TopicCategory_s` (campo canonico); in mancanza, cerca una
    categoria ISO nota sia tra le `keywords_s` sia tra i `categories` del record.
    """
    topic = source.get("apiso_TopicCategory_s")
    if isinstance(topic, list):
        topic = topic[0] if topic else None
    if topic:
        return cast(str, topic)
    keywords = source.get("keywords_s")
    if isinstance(keywords, str):
        keywords = [keywords]
    candidates = list(keywords or []) + [c.get("term") for c in categories]
    return next((k for k in candidates if k in DATA_CATEGORIES), None)


def compact_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Riduce la risposta di :func:`search` a record sintetici per agenti/pipe.

    Una voce per risultato con i soli campi ad alto segnale: ``id``, ``title``,
    ``org`` (ente responsabile da ``apiso_OrganizationName_txt``, più informativo
    di ``author.name``), ``type``, ``category`` (ISO 19115), ``updated`` e
    ``resources`` (tipi di servizio/download fruibili). Pensata per l'output
    ``--format compact`` (NDJSON), ma utilizzabile direttamente come libreria.
    """
    records: list[dict[str, Any]] = []
    for r in payload.get("results", []) or []:
        source = r.get("_source") or {}
        categories = r.get("categories") or []
        org = source.get("apiso_OrganizationName_txt") or (r.get("author") or {}).get("name")
        records.append(
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "org": org,
                "type": source.get("apiso_Type_s"),
                "category": _topic_category(source, categories),
                "updated": r.get("updated"),
                "resources": _resource_types(r.get("links") or []),
            }
        )
    return records
