"""openrndt — CLI Python per il Repertorio Nazionale dei Dati Territoriali."""

from openrndt._version import __version__
from openrndt.cli import main
from openrndt.item import (
    AmbiguousItemIdError,
    ItemNotFoundError,
    get_item,
    get_item_html,
    get_item_xml,
    resolve_item_id,
)
from openrndt.search import (
    bbox_from_envelope,
    compact_results,
    contact_point,
    download_urls,
    item_record,
    organization_names,
    record_dates,
    record_license,
    record_url,
    search,
)

__all__ = [
    "main",
    "search",
    "compact_results",
    "record_dates",
    "record_license",
    "record_url",
    "organization_names",
    "item_record",
    "contact_point",
    "download_urls",
    "bbox_from_envelope",
    "get_item",
    "get_item_xml",
    "get_item_html",
    "resolve_item_id",
    "ItemNotFoundError",
    "AmbiguousItemIdError",
    "__version__",
]
