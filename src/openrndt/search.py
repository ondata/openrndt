"""Chiamata e parsing di /rest/metadata/search."""

from __future__ import annotations

from typing import Any

from openrndt.client import rndt_request

SEARCH_PATH = "/rest/metadata/search"
MAX_NUM = 5000


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
