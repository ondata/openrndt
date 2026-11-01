"""Chiamate a /rest/metadata/item/{id} per dettaglio singolo metadato."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

import httpx

from openrndt.client import rndt_request
from openrndt.search import SEARCH_PATH, catalog_ids_for_fileid

ITEM_PATH = "/rest/metadata/item"

# UUID nudo, senza prefisso d'ente: la forma canonica del catalogo è `prefisso:uuid`
# (es. `r_sicili:7832b30d-…`), l'endpoint item non risolve la forma senza prefisso.
BARE_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


class ItemNotFoundError(Exception):
    def __init__(self, item_id: str) -> None:
        self.item_id = item_id
        super().__init__(f"Metadato non trovato: {item_id}")


class AmbiguousItemIdError(Exception):
    """L'UUID nudo corrisponde a più ID namespaced nel catalogo."""

    def __init__(self, item_id: str, candidates: list[str]) -> None:
        self.item_id = item_id
        self.candidates = candidates
        super().__init__(
            f"ID ambiguo: {item_id} corrisponde a più metadati ({', '.join(candidates)}). Passare l'ID completo."
        )


def _encode_id(item_id: str) -> str:
    return quote(item_id, safe="")


def resolve_item_id(item_id: str) -> str:
    """Ritorna l'ID namespaced (`prefisso:uuid`) di un metadato.

    Un ID già in forma `prefisso:uuid` (o qualsiasi forma non-UUID) torna
    invariato. Un UUID nudo non è risolvibile dall'endpoint item, che accetta
    solo la forma completa: si risolve con una ricerca e si tiene l'unico
    risultato il cui ID contiene l'UUID (la ricerca testuale su un UUID porta
    anche falsi positivi, es. numeri nel testo). Zero risultati solleva
    ``ItemNotFoundError``, più di uno ``AmbiguousItemIdError``.
    """
    if not BARE_UUID_RE.match(item_id):
        return item_id
    response = rndt_request(SEARCH_PATH, params={"f": "json", "start": 1, "num": 20, "q": item_id})
    response.raise_for_status()
    results: list[dict[str, Any]] = response.json().get("results") or []
    needle = item_id.lower()
    hits = [r for r in results if needle in str(r.get("id", "")).lower()]
    if not hits:
        raise ItemNotFoundError(item_id)
    if len(hits) > 1:
        raise AmbiguousItemIdError(item_id, [str(r["id"]) for r in hits])
    return str(hits[0]["id"])


def get_item(item_id: str) -> dict[str, Any]:
    """JSON Elasticsearch del singolo metadato (_source + flag).

    Un UUID nudo viene prima risolto nella forma `prefisso:uuid` (vedi
    :func:`resolve_item_id`). Un id che il catalogo non ha come ``_id`` si
    cerca anche come ``fileid`` (vedi :func:`openrndt.search.catalog_ids_for_fileid`).
    Solleva ``ItemNotFoundError`` se l'ID non esiste
    e ``httpx.HTTPError`` (status o rete) se la richiesta fallisce. Una
    risposta con body non-JSON valido (pur status 2xx) solleva
    ``json.JSONDecodeError`` (``ValueError``).
    """
    resolved = resolve_item_id(item_id)
    data = _fetch_item(resolved)
    if data.get("found") is False:
        data = _fetch_item(_catalog_id_from_fileid(item_id, resolved))
        if data.get("found") is False:
            raise ItemNotFoundError(item_id)
    return data


def _catalog_id_from_fileid(item_id: str, resolved: str) -> str:
    """L'``_id`` del catalogo per un id che il catalogo ha solo come fileid (schede AGEA).

    ``ItemNotFoundError`` se nessuna scheda ha quel fileid, ``AmbiguousItemIdError``
    se più d'una.
    """
    ids = [i for i in catalog_ids_for_fileid(resolved) if i != resolved]
    if not ids:
        raise ItemNotFoundError(item_id)
    if len(ids) > 1:
        raise AmbiguousItemIdError(item_id, ids)
    return ids[0]


def _fetch_item(item_id: str) -> dict[str, Any]:
    response = rndt_request(f"{ITEM_PATH}/{_encode_id(item_id)}")
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    return data


def _fetch_text(item_id: str, suffix: str) -> str:
    """XML o HTML della scheda. Per un id che non esiste come ``_id`` il server
    risponde 500 (xml) o 501 (html): si riprova dal fileid, come in :func:`get_item`."""
    resolved = resolve_item_id(item_id)
    try:
        response = rndt_request(f"{ITEM_PATH}/{_encode_id(resolved)}/{suffix}")
        response.raise_for_status()
    except httpx.HTTPStatusError:
        catalog_id = _catalog_id_from_fileid(item_id, resolved)
        response = rndt_request(f"{ITEM_PATH}/{_encode_id(catalog_id)}/{suffix}")
        response.raise_for_status()
    return response.text


def get_item_xml(item_id: str) -> str:
    """XML ISO 19139 (gmd:MD_Metadata). Accetta anche un UUID nudo o un fileid diverso dall'``_id``."""
    return _fetch_text(item_id, "xml")


def get_item_html(item_id: str) -> str:
    """HTML pronto per renderizzare. Accetta anche un UUID nudo o un fileid diverso dall'``_id``."""
    return _fetch_text(item_id, "html")
