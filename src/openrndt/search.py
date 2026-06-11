"""Chiamata e parsing di /rest/metadata/search."""

from __future__ import annotations

from typing import Any

from openrndt.client import rndt_request
from openrndt.codelists import DATA_CATEGORIES

SEARCH_PATH = "/rest/metadata/search"
MAX_NUM = 5000

# Link `rel` che NON sono risorse fruibili (rappresentazioni del metadato stesso).
_NON_RESOURCE_RELS = {"alternate", "icon", "self"}


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


def search(
    *,
    q: str | None = None,
    bbox: str | None = None,
    data_category: str | None = None,
    time: str | None = None,
    modified: str | None = None,
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

    params: dict[str, Any] = {"f": fmt, "start": start, "num": num}
    q_parts: list[str] = []
    if q:
        q_parts.append(f"({q})" if data_category else q)
    if data_category:
        clause = _build_category_clause(data_category)
        if clause:
            q_parts.append(clause)
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
        return response.json()
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

    Preferisce `apiso_TopicCategory_s` (campo canonico); in mancanza, cerca tra le
    keyword una che corrisponda a una categoria ISO nota.
    """
    topic = source.get("apiso_TopicCategory_s")
    if isinstance(topic, list):
        topic = topic[0] if topic else None
    if topic:
        return topic
    keywords = source.get("keywords_s")
    if isinstance(keywords, str):
        keywords = [keywords]
    if not keywords:
        keywords = [c.get("term") for c in categories]
    return next((k for k in keywords if k in DATA_CATEGORIES), None)


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
