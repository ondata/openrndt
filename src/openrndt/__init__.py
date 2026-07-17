"""openrndt — CLI Python per il Repertorio Nazionale dei Dati Territoriali."""

from openrndt.cli import main
from openrndt.item import ItemNotFoundError, get_item, get_item_html, get_item_xml
from openrndt.search import search

__version__ = "1.0.0"
__all__ = ["main", "search", "get_item", "get_item_xml", "get_item_html", "ItemNotFoundError", "__version__"]
