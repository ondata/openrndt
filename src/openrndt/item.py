"""Chiamate a /rest/metadata/item/{id} per dettaglio singolo metadato."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from openrndt.client import rndt_request
from openrndt.search import SEARCH_PATH

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
    :func:`resolve_item_id`). Solleva ``ItemNotFoundError`` se l'ID non esiste
    e ``httpx.HTTPError`` (status o rete) se la richiesta fallisce. Una
    risposta con body non-JSON valido (pur status 2xx) solleva
    ``json.JSONDecodeError`` (``ValueError``).
    """
    response = rndt_request(f"{ITEM_PATH}/{_encode_id(resolve_item_id(item_id))}")
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    if data.get("found") is False:
        raise ItemNotFoundError(item_id)
    return data


def get_item_xml(item_id: str) -> str:
    """XML ISO 19139 (gmd:MD_Metadata). Accetta anche un UUID nudo."""
    response = rndt_request(f"{ITEM_PATH}/{_encode_id(resolve_item_id(item_id))}/xml")
    response.raise_for_status()
    return response.text


def get_item_html(item_id: str) -> str:
    """HTML pronto per renderizzare. Accetta anche un UUID nudo."""
    response = rndt_request(f"{ITEM_PATH}/{_encode_id(resolve_item_id(item_id))}/html")
    response.raise_for_status()
    return response.text
