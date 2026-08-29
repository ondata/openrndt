"""openrndt — CLI Python per il Repertorio Nazionale dei Dati Territoriali."""

from openrndt._version import __version__
from openrndt.cli import main
from openrndt.item import ItemNotFoundError, get_item, get_item_html, get_item_xml
from openrndt.search import (
    compact_results,
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
    "get_item",
    "get_item_xml",
    "get_item_html",
    "ItemNotFoundError",
    "__version__",
]
