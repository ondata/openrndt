"""Chiamata e parsing di /rest/metadata/search."""

from __future__ import annotations

from datetime import date
import re
from typing import Any, cast
from urllib.parse import quote

from openrndt.client import rndt_request
from openrndt.codelists import DATA_CATEGORIES
from openrndt.resources import extract_resources

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


def _validate_bbox(bbox: str) -> None:
    """Verifica la forma di `bbox` prima di interrogare l'API.

    Serve perché il RNDT ignora in silenzio una bbox malformata e risponde con
    l'intero catalogo: `bbox="non,valido"` e `bbox="12,45,11"` restituivano
    23.738 record con exit code 0, cioè un falso successo per chi controlla solo
    il numero di risultati. Una bbox invertita fa invece rispondere 500.
    """
    parts = [p.strip() for p in bbox.split(",")]
    if len(parts) != 4:
        raise ValueError(f"`bbox` richiede quattro valori xmin,ymin,xmax,ymax (ricevuti {len(parts)}: {bbox!r}).")
    try:
        xmin, ymin, xmax, ymax = (float(p) for p in parts)
    except ValueError:
        raise ValueError(f"`bbox` accetta solo numeri: {bbox!r}.") from None
    for name, value in (("xmin", xmin), ("xmax", xmax)):
        if not -180 <= value <= 180:
            raise ValueError(f"`bbox`: {name}={value} fuori dall'intervallo delle longitudini (-180..180).")
    for name, value in (("ymin", ymin), ("ymax", ymax)):
        if not -90 <= value <= 90:
            raise ValueError(f"`bbox`: {name}={value} fuori dall'intervallo delle latitudini (-90..90).")
    if xmin >= xmax:
        raise ValueError(f"`bbox`: xmin ({xmin}) deve essere minore di xmax ({xmax}).")
    if ymin >= ymax:
        raise ValueError(f"`bbox`: ymin ({ymin}) deve essere minore di ymax ({ymax}).")


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
        _validate_bbox(bbox)
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


# Valori di `isOpendata` che dichiarano soltanto "questo è un open data" senza
# nominare una licenza. Vanno tolti perché altrimenti il campo `license` degli
# output riporterebbe il marcatore al posto della licenza.
_OPENDATA_MARKERS = {"opendata", "open data"}


def record_license(source: dict[str, Any]) -> tuple[bool, str | None]:
    """Licenza dichiarata da un record: ``(open, license)``.

    ``open`` è vero quando ``isOpendata`` è presente e non vuoto, cioè quando la
    scheda si dichiara open data. ``license`` sono i valori dello stesso campo
    diversi dal marcatore, uniti da ``; ``, riportati **come sono**: il RNDT non
    li normalizza e nello stesso campo convivono ``CC BY 4.0``, ``CCBY``, URL e
    interi paragrafi di disclaimer. ``None`` se resta solo il marcatore.

    Misurato su 3000 record (2026-08-29): ``isOpendata`` è presente sul 72%, ma
    1177 di quei record sono dell'Agenzia delle Entrate e senza di essi la
    copertura scende al 55%; in un terzo dei casi contiene il solo marcatore.
    Alcuni dataset aperti dichiarano la licenza soltanto in
    ``apiso_OtherConstraints_s`` o ``apiso_ConditionApplyingToAccessAndUse_txt``
    e qui risultano ``open=False``: il campo dice cosa ha dichiarato l'ente, non
    se il dato sia riusabile.
    """
    raw = source.get("isOpendata")
    values = raw if isinstance(raw, list) else [raw] if raw is not None else []
    texts = [v.strip() for v in values if isinstance(v, str) and v.strip()]
    if not texts:
        return (False, None)
    named = [v for v in texts if v.lower() not in _OPENDATA_MARKERS]
    return (True, "; ".join(named) if named else None)


def record_url(result: dict[str, Any]) -> str | None:
    """Permalink della scheda sul portale, dai link del record.

    È il link ``rel="alternate"`` di tipo ``text/html``, cioè la pagina pubblica
    citabile del metadato (presente su 200 record su 200 in un campione del
    2026-08-29). ``None`` se il record non lo espone.
    """
    for link in result.get("links") or []:
        if not isinstance(link, dict):
            continue
        if link.get("rel") == "alternate" and link.get("type") == "text/html":
            href = link.get("href")
            if isinstance(href, str) and href:
                return href
    return None


def _first_str(value: Any) -> str | None:
    """Primo valore stringa non vuoto di un campo che arriva scalare o array."""
    if isinstance(value, list):
        value = next((v for v in value if isinstance(v, str) and v), None)
    return value if isinstance(value, str) and value else None


def contact_point(source: dict[str, Any]) -> dict[str, str | None]:
    """Punto di contatto designato del dataset: nome, email e sito web."""
    return {
        "name": _first_str(source.get("PuntoDiContatto_s")),
        "email": _first_str(source.get("PuntoDiContattoEmail_s")),
        "website": _first_str(source.get("PuntoDiContattoSitoWeb_s")),
    }


def download_urls(source: dict[str, Any]) -> list[str]:
    """URL di download dichiarati: ``url_download_s`` + ``url_http_download_s``.

    I due campi arrivano con tipi incoerenti (scalare o array) a seconda della
    scheda: la normalizzazione in lista mantiene l'ordine dei campi e scarta i
    valori non stringa. I contenuti non vengono giudicati: il RNDT mette qui
    anche URL che non sono download diretti (verificato: un GetCapabilities
    WMS dentro ``url_http_download_s``).
    """
    urls: list[str] = []
    for field in ("url_download_s", "url_http_download_s"):
        value = source.get(field)
        if isinstance(value, list):
            urls.extend(u for u in value if isinstance(u, str) and u)
        elif isinstance(value, str) and value:
            urls.append(value)
    return urls


def bbox_from_envelope(envelope: Any) -> dict[str, float] | None:
    """bbox ``{xmin,ymin,xmax,ymax}`` dall'``envelope_geo`` Elasticsearch.

    L'envelope ha coordinate ``[[xmin, ymax], [xmax, ymin]]`` (angolo nord-ovest
    e sud-est). ``None`` se assente o malformato: nessuna bbox inventata.
    """
    try:
        coords = envelope[0]["coordinates"]
        (xmin, ymax), (xmax, ymin) = coords
        return {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax}
    except (IndexError, KeyError, TypeError, ValueError):
        return None


# Path del permalink pubblico della scheda: lo stesso che il server mette nei
# link `alternate` delle risposte di ricerca. L'endpoint `item` non espone quei
# link, per cui il permalink va costruito dall'id.
CATALOG_PERMALINK = "https://geodati.gov.it/geoportal-catalog/rest/metadata/item"


def item_record(payload: dict[str, Any]) -> dict[str, Any]:
    """Documento normalizzato di ``get``: vocabolario di ``search`` + dettaglio.

    Espande la busta Elasticsearch in un oggetto con gli stessi campi delle
    risposte di ricerca (``id``, ``title``, ``org``, ``category``, e le date
    ``updated``/``indexed`` con la stessa semantica di ``compact``), più i
    dettagli utili alla scheda: ``data_date`` (del dato, non della scheda),
    ``contact`` (nome/email/sito del punto di contatto designato), ``bbox``
    (da ``envelope_geo``), ``lineage``, ``resources`` (come ``resources``
    senza check) e ``url`` (permalink citabile). ``_source`` e i flag della
    busta sono preservati inalterati per chi li usa già.
    """
    source = payload.get("_source") or {}
    updated, indexed = record_dates(payload)
    is_open, license_text = record_license(source)
    item_id = _first_str(source.get("fileid")) or payload.get("_id")
    record: dict[str, Any] = {
        "id": item_id,
        "title": _first_str(source.get("title")),
        "description": _first_str(source.get("description")),
        "org": _first_str(source.get("apiso_OrganizationName_txt"))
        or _first_str(source.get("EnteResponsabile_s")),
        "type": _first_str(source.get("apiso_Type_s")),
        "category": _topic_category(source, []),
        "updated": updated,
        "indexed": indexed,
        "data_date": (
            _first_str(source.get("apiso_RevisionDate_dt"))
            or _first_str(source.get("apiso_CreationDate_dt"))
            or _first_str(source.get("apiso_PublicationDate_dt"))
        ),
        "open": is_open,
        "license": license_text,
        "contact": contact_point(source),
        "bbox": bbox_from_envelope(source.get("envelope_geo")),
        "lineage": _first_str(source.get("apiso_Lineage_txt")),
        "resources": extract_resources(payload),
        "url": (
            f"{CATALOG_PERMALINK}/{quote(str(item_id), safe='')}/html"
            if item_id
            else None
        ),
    }
    for key in ("_index", "_id", "_version", "_seq_no", "_primary_term", "found", "_source"):
        if key in payload:
            record[key] = payload[key]
    return record


def compact_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Riduce la risposta di :func:`search` a record sintetici per agenti/pipe.

    Una voce per risultato con i soli campi ad alto segnale: ``id``, ``title``,
    ``org`` (ente responsabile da ``apiso_OrganizationName_txt``, più informativo
    di ``author.name``), ``type``, ``category`` (ISO 19115), ``updated`` (data
    della scheda), ``indexed`` (indicizzazione nel catalogo), 
    ``open`` e ``license`` (vedi :func:`record_license`), ``url`` (permalink della scheda)
    e ``resources`` (tipi di servizio/download fruibili), ``email`` (punto di contatto
    designato, vedi :func:`contact_point`) e ``download`` (URL dichiarati, vedi
    :func:`download_urls`). Pensata per l'output ``--format compact`` (NDJSON), ma
    utilizzabile direttamente come libreria.
    """
    records: list[dict[str, Any]] = []
    for r in payload.get("results", []) or []:
        source = r.get("_source") or {}
        categories = r.get("categories") or []
        org = source.get("apiso_OrganizationName_txt") or (r.get("author") or {}).get("name")
        updated, indexed = record_dates(r)
        is_open, license_text = record_license(source)
        records.append(
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "org": org,
                "type": source.get("apiso_Type_s"),
                "category": _topic_category(source, categories),
                "updated": updated,
                "indexed": indexed,
                "open": is_open,
                "license": license_text,
                "url": record_url(r),
                "resources": _resource_types(r.get("links") or []),
                "email": _first_str(source.get("PuntoDiContattoEmail_s")),
                "download": download_urls(source),
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
