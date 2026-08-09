"""openrndt — CLI Python per il Repertorio Nazionale dei Dati Territoriali."""

from openrndt._version import __version__
from openrndt.cli import main
from openrndt.item import ItemNotFoundError, get_item, get_item_html, get_item_xml
from openrndt.search import search

__all__ = ["main", "search", "get_item", "get_item_xml", "get_item_html", "ItemNotFoundError", "__version__"]
