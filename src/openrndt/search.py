"""Chiamata e parsing di /rest/metadata/search."""

from __future__ import annotations

from datetime import date
import re
from typing import Any, cast

from openrndt.client import rndt_request
from openrndt.codelists import DATA_CATEGORIES

SEARCH_PATH = "/rest/metadata/search"
MAX_NUM = 5000

# Campo dell'ente su cui cerca `org`: analizzato, quindi case-insensitive e
# insensibile all'ordine dei token. Verificato live: la frase esatta funziona
# (`"comune di torino"` → 269 record, un solo ente), mentre la wildcard su
# `contact_organizations_s` è case-sensitive e prende ogni record che *nomina*
# quel territorio, anche di altri enti.
ORG_FIELD = "apiso_OrganizationName_txt"
# Campo dell'ente in forma keyword: confronto esatto, case-sensitive.
ORG_EXACT_FIELD = "EnteResponsabile_s"

# Link `rel` che NON sono risorse fruibili (rappresentazioni del metadato stesso).
_NON_RESOURCE_RELS = {"alternate", "icon", "self"}
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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


def _normalize_bbox_crs(bbox_crs: str | None) -> str | None:
    if bbox_crs is None:
        return None
    norm = bbox_crs.strip().upper().replace(":", "")
    if norm in {"EPSG4326", "CRS84", "WGS84"}:
        return "EPSG:4326"
    raise ValueError(
        "`bbox_crs` non supportato: usare EPSG:4326 (alias accettati: CRS:84, WGS84)."
    )


def _validate_iso_date(value: str, *, param_name: str) -> None:
    if not _ISO_DATE_RE.match(value):
        raise ValueError(f"`{param_name}` deve essere nel formato yyyy-mm-dd.")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"`{param_name}` non è una data di calendario valida.") from exc


def _build_date_range_clause(field: str, start: str | None, end: str | None, *, label: str) -> str | None:
    if start is None and end is None:
        return None
    if start is not None:
        _validate_iso_date(start, param_name=f"{label}_from")
    if end is not None:
        _validate_iso_date(end, param_name=f"{label}_to")
    lower = f"{start}T00:00:00Z" if start is not None else "*"
    upper = f"{end}T23:59:59Z" if end is not None else "*"
    return f"{field}:[{lower} TO {upper}]"


def _escape_phrase(value: str) -> str:
    """Prepara un valore per una clausola Lucene tra virgolette."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _build_org_clause(org: str | None, org_exact: str | None) -> str | None:
    """Clausola Lucene per la ricerca per ente.

    ``org`` cerca la frase sul campo analizzato (``apiso_OrganizationName_txt``):
    case-insensitive, robusta rispetto a maiuscole e apostrofi. ``org_exact``
    confronta il valore esatto sul campo keyword (``EnteResponsabile_s``), utile
    quando si conosce già la stringa memorizzata in catalogo.
    """
    if org is not None and org_exact is not None:
        raise ValueError("Usa `org` oppure `org_exact`, non entrambi.")
    if org is not None:
        value = org.strip()
        if not value:
            raise ValueError("`org` non può essere vuoto.")
        return f'{ORG_FIELD}:"{_escape_phrase(value)}"'
    if org_exact is not None:
        value = org_exact.strip()
        if not value:
            raise ValueError("`org_exact` non può essere vuoto.")
        return f'{ORG_EXACT_FIELD}:"{_escape_phrase(value)}"'
    return None


def search(
    *,
    q: str | None = None,
    bbox: str | None = None,
    bbox_crs: str | None = None,
    org: str | None = None,
    org_exact: str | None = None,
    data_category: str | None = None,
    time: str | None = None,
    modified: str | None = None,
    updated_from: str | None = None,
    updated_to: str | None = None,
    published_from: str | None = None,
    published_to: str | None = None,
    sort: str | None = None,
    start: int = 1,
    num: int = 10,
    fmt: str = "json",
    item_id: str | None = None,
) -> dict[str, Any] | str:
    """Esegue una ricerca su /rest/metadata/search.

    Ritorna un dict (parsed JSON) se `fmt` è `json` o `json-source`,
    altrimenti la stringa con il body grezzo (XML, CSV, KML, …).

    ``org`` e ``org_exact`` (mutuamente esclusivi) filtrano per ente: il primo
    sul campo analizzato ``apiso_OrganizationName_txt`` (case-insensitive), il
    secondo sul keyword ``EnteResponsabile_s`` (esatto). Entrambi si combinano
    in AND con gli altri filtri.

    Nota su `sort` (verificato live): l'ordinamento reale usa la sintassi
    `campo:asc|desc` su un campo sortable (keyword `_s`, data `_dt`, intero `_i`),
    es. ``sort="apiso_Modified_dt:desc"``. I valori ``dateDescending`` /
    ``dateAscending`` documentati ufficialmente NON ordinano (vengono ignorati).
    Non esiste un campo data-di-pubblicazione ordinabile: il proxy più affidabile
    per "ultimi pubblicati" è ``apiso_Modified_dt``.

    Solleva ``ValueError`` su parametri non validi e ``httpx.HTTPError`` (incluse
    ``httpx.HTTPStatusError`` per le risposte 4xx/5xx e ``httpx.ConnectError`` /
    ``httpx.TimeoutException`` per i problemi di rete) se la richiesta fallisce.
    Con ``fmt`` JSON, una risposta con body non-JSON valido (pur status 2xx)
    solleva ``json.JSONDecodeError`` (sottoclasse di ``ValueError``).
    """
    if num > MAX_NUM:
        raise ValueError(f"`num` non può superare {MAX_NUM} (richiesto: {num}).")
    if start < 1:
        raise ValueError("`start` deve essere ≥ 1.")
    if bbox_crs is not None and bbox is None:
        raise ValueError("`bbox_crs` richiede anche `bbox`.")
    if bbox is not None:
        _normalize_bbox_crs(bbox_crs)
    if modified is not None and (updated_from is not None or updated_to is not None):
        raise ValueError("Usa `modified` oppure `updated_from/updated_to`, non entrambi.")

    params: dict[str, Any] = {"f": fmt, "start": start, "num": num}
    non_q_clauses: list[str] = []
    org_clause = _build_org_clause(org, org_exact)
    if org_clause:
        non_q_clauses.append(org_clause)
    if data_category:
        clause = _build_category_clause(data_category)
        if clause:
            non_q_clauses.append(clause)
    updated_clause = _build_date_range_clause("apiso_Modified_dt", updated_from, updated_to, label="updated")
    if updated_clause:
        non_q_clauses.append(updated_clause)
    published_clause = _build_date_range_clause(
        "apiso_PublicationDate_dt", published_from, published_to, label="published"
    )
    if published_clause:
        non_q_clauses.append(published_clause)
    q_parts: list[str] = []
    if q:
        q_parts.append(f"({q})" if non_q_clauses else q)
    q_parts.extend(non_q_clauses)
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
        data: dict[str, Any] = response.json()
        return data
    return response.text


def _resource_types(links: list[dict[str, Any]]) -> list[str]:
    """Tipi di risorsa fruibile (WMS/WFS/download/…) dedotti dai `links`.

    Esclude le rappresentazioni del metadato (rel alternate/icon/self) e tiene i
    `dctype` valorizzati; un `rel=enclosure` senza dctype è un download diretto.
    """
    types: set[str] = set()
    for link in links:
        if link.get("rel") in _NON_RESOURCE_RELS:
            continue
        dctype = link.get("dctype")
        if dctype:
            types.add(dctype)
        elif link.get("rel") == "enclosure":
            types.add("download")
    return sorted(types)


def _topic_category(source: dict[str, Any], categories: list[dict[str, Any]]) -> str | None:
    """Categoria ISO 19115 del record.

    Preferisce `apiso_TopicCategory_s` (campo canonico); in mancanza, cerca una
    categoria ISO nota sia tra le `keywords_s` sia tra i `categories` del record.
    """
    topic = source.get("apiso_TopicCategory_s")
    if isinstance(topic, list):
        topic = topic[0] if topic else None
    if topic:
        return cast(str, topic)
    keywords = source.get("keywords_s")
    if isinstance(keywords, str):
        keywords = [keywords]
    candidates = list(keywords or []) + [c.get("term") for c in categories]
    return next((k for k in candidates if k in DATA_CATEGORIES), None)


def record_dates(result: dict[str, Any]) -> tuple[str | None, str | None]:
    """Date di un risultato: ``(updated, indexed)``.

    ``updated`` è la data della scheda di metadato (``apiso_Modified_dt``): è la
    stessa su cui filtrano ``updated_from``/``updated_to`` ed è l'unico campo
    data valorizzato su tutto il catalogo. ``indexed`` è l'istante in cui il
    record è stato indicizzato dal catalogo (``sys_modified_dt``, esposto
    dall'API come campo top-level ``updated``): non dice nulla né sul dato né
    sulla scheda, e varia a blocchi con le reindicizzazioni.
    """
    source = result.get("_source") or {}
    updated = source.get("apiso_Modified_dt")
    if isinstance(updated, list):
        updated = updated[0] if updated else None
    indexed = source.get("sys_modified_dt") or result.get("updated")
    # I valori arrivano da JSON non tipizzato: verificarli invece di asserirli
    # con un cast, così un campo di forma inattesa diventa None e non un tipo
    # sbagliato che si propaga silenziosamente negli output.
    return (
        updated if isinstance(updated, str) else None,
        indexed if isinstance(indexed, str) else None,
    )


def compact_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Riduce la risposta di :func:`search` a record sintetici per agenti/pipe.

    Una voce per risultato con i soli campi ad alto segnale: ``id``, ``title``,
    ``org`` (ente responsabile da ``apiso_OrganizationName_txt``, più informativo
    di ``author.name``), ``type``, ``category`` (ISO 19115), ``updated`` (data
    della scheda), ``indexed`` (indicizzazione nel catalogo) e ``resources``
    (tipi di servizio/download fruibili). Pensata per l'output
    ``--format compact`` (NDJSON), ma utilizzabile direttamente come libreria.
    """
    records: list[dict[str, Any]] = []
    for r in payload.get("results", []) or []:
        source = r.get("_source") or {}
        categories = r.get("categories") or []
        org = source.get("apiso_OrganizationName_txt") or (r.get("author") or {}).get("name")
        updated, indexed = record_dates(r)
        records.append(
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "org": org,
                "type": source.get("apiso_Type_s"),
                "category": _topic_category(source, categories),
                "updated": updated,
                "indexed": indexed,
                "resources": _resource_types(r.get("links") or []),
            }
        )
    return records


def organization_names(payload: dict[str, Any]) -> list[str]:
    """Nomi di ente distinti presenti nei risultati, in ordine di frequenza.

    L'API RNDT ignora il parametro ``facet``: l'unico modo per scoprire come un
    ente è scritto in catalogo è aggregare a valle un campione di risultati.
    """
    counts: dict[str, int] = {}
    for r in payload.get("results", []) or []:
        source = r.get("_source") or {}
        for field in (ORG_EXACT_FIELD, "apiso_OrganizationName_txt"):
            value = source.get(field)
            if isinstance(value, str) and value.strip():
                counts[value] = counts.get(value, 0) + 1
                break
    return [name for name, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
