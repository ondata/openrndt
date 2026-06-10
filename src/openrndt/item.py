"""Chiamate a /rest/metadata/item/{id} per dettaglio singolo metadato."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from openrndt.client import rndt_request

ITEM_PATH = "/rest/metadata/item"


def _encode_id(item_id: str) -> str:
    return quote(item_id, safe="")


def get_item(item_id: str) -> dict[str, Any]:
    """JSON Elasticsearch del singolo metadato (_source + flag)."""
    response = rndt_request(f"{ITEM_PATH}/{_encode_id(item_id)}")
    response.raise_for_status()
    return response.json()


def get_item_xml(item_id: str) -> str:
    """XML ISO 19139 (gmd:MD_Metadata)."""
    response = rndt_request(f"{ITEM_PATH}/{_encode_id(item_id)}/xml")
    response.raise_for_status()
    return response.text


def get_item_html(item_id: str) -> str:
    """HTML pronto da renderizzare."""
    response = rndt_request(f"{ITEM_PATH}/{_encode_id(item_id)}/html")
    response.raise_for_status()
    return response.text
