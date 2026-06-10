"""openrndt — CLI Python per il Repertorio Nazionale dei Dati Territoriali."""

from openrndt.cli import main
from openrndt.item import get_item, get_item_xml, get_item_html
from openrndt.search import search

__version__ = "0.1.0"
__all__ = ["main", "search", "get_item", "get_item_xml", "get_item_html", "__version__"]
