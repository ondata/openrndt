"""openrndt — CLI Python per il Repertorio Nazionale dei Dati Territoriali."""

from openrndt._version import __version__
from openrndt.cli import main
from openrndt.ipa import find_ipa, ipa_clause, ipa_vocabulary, ipa_vocabulary_date
from openrndt.item import (
    AmbiguousItemIdError,
    ItemNotFoundError,
    get_item,
    get_item_html,
    get_item_xml,
    resolve_item_id,
)
from openrndt.resources import (
    capabilities_url,
    check_resources,
    extract_resources,
    list_layers,
    parse_wms_capabilities,
    service_base_url,
    wms_layer_crs,
)
from openrndt.search import (
    bbox_from_envelope,
    compact_results,
    contact_point,
    download_urls,
    geolibre_search_url,
    geolibre_url,
    item_record,
    organization_names,
    record_dates,
    record_license,
    record_org,
    record_url,
    results_bbox,
    search,
)

__all__ = [
    "find_ipa",
    "ipa_clause",
    "ipa_vocabulary",
    "ipa_vocabulary_date",
    "main",
    "search",
    "compact_results",
    "record_dates",
    "record_license",
    "record_org",
    "record_url",
    "results_bbox",
    "geolibre_search_url",
    "geolibre_url",
    "extract_resources",
    "check_resources",
    "list_layers",
    "parse_wms_capabilities",
    "wms_layer_crs",
    "capabilities_url",
    "service_base_url",
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
