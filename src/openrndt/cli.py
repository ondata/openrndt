"""CLI Typer di openrndt."""

from __future__ import annotations

import json
from typing import Any, NoReturn, cast

import httpx
import typer

from openrndt import codelists, config, output
from openrndt._version import __version__
from openrndt.item import ItemNotFoundError, get_item, get_item_html, get_item_xml
from openrndt.resources import check_resources, extract_resources
from openrndt.search import (
    ORG_EXACT_FIELD,
    compact_results,
    organization_names,
    record_dates,
)
from openrndt.search import search as do_search

app = typer.Typer(
    help=(
        "openrndt — CLI per il Repertorio Nazionale dei Dati Territoriali.\n\n"
        "Variabili d'ambiente:\n"
        f"  {config.ENV_BASE_URL}   Override del base URL "
        f"(default: {config.DEFAULT_BASE_URL}).\n"
    ),
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> bool:
    if value:
        typer.echo(f"openrndt {__version__}")
        raise typer.Exit(0)
    # Click usa il valore di ritorno del callback come valore dell'opzione:
    # restituire None renderebbe `version` None invece che False.
    return value


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Stampa la versione di openrndt ed esce.",
        callback=_version_callback,
        is_eager=True,
    ),
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        help=f"Override del base URL RNDT (default: env {config.ENV_BASE_URL} o {config.DEFAULT_BASE_URL}).",
    ),
    timeout: float | None = typer.Option(
        None,
        "--timeout",
        help=f"Timeout HTTP in secondi per singolo tentativo (default: {config.DEFAULT_TIMEOUT}). "
        "Con i retry su timeout/5xx (3 tentativi), il caso peggiore è ~3x questo valore.",
    ),
    fmt: str | None = typer.Option(
        None,
        "--format",
        "-F",
        help=(
            "Formato di output: json (default), table, csv, compact (NDJSON per agenti, solo per search). "
            "Se omesso, `search --profile` passa automaticamente a table."
        ),
        case_sensitive=False,
    ),
) -> None:
    config.set_base_url(base_url)
    config.set_timeout(timeout)
    if fmt is None:
        output.set_mode("json", explicit=False)
    else:
        try:
            output.set_mode(fmt.lower())
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(2)


def _http_error(exc: httpx.HTTPError, *, sort: str | None = None) -> NoReturn:
    """Stampa un messaggio leggibile su stderr ed esce 1 — mai uno stack trace.

    Distingue una risposta HTTP di errore (status) da un problema di rete
    (connessione rifiutata, timeout dopo i retry, DNS): in entrambi i casi
    l'agente che orchestra la CLI deve capire l'esito dal solo output.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        typer.echo(f"Errore HTTP {exc.response.status_code}: {exc.request.url}", err=True)
        if sort:
            typer.echo(
                "Se l'errore riguarda --sort: su RNDT ordinano solo `title` e "
                "`apiso_Modified_dt` (forma campo:asc|desc); `dateAscending`, "
                "`dateDescending` e `relevance` sono ignorati. "
                "Vedi `discover --what sort_values`.",
                err=True,
            )
    else:
        url = getattr(getattr(exc, "request", None), "url", None) or config.get_base_url()
        typer.echo(
            f"Errore di rete: impossibile contattare {url} ({type(exc).__name__}).",
            err=True,
        )
    raise typer.Exit(1)


_RAW_DATE_NOTE = (
    "Nota sulle date: nel JSON grezzo dell'API il campo top-level `updated` è "
    "l'istante di indicizzazione nel catalogo (`_source.sys_modified_dt`), non la "
    "data della scheda. La data della scheda — quella su cui filtrano "
    "--updated-from/--updated-to — è `_source.apiso_Modified_dt`. Negli output "
    "table/csv/compact i due campi si chiamano `updated` e `indexed`."
)


def _table_date_caption(row: dict[str, Any]) -> str | None:
    """Legenda sotto la tabella: quale data è quale."""
    if "updated" not in row:
        return None
    caption = "updated = data della scheda (apiso_Modified_dt)"
    if "indexed" in row:
        caption += " · indexed = indicizzazione nel catalogo"
    return caption


def _uses_date_filters(sort: str | None, *filters: str | None) -> bool:
    """True se la ricerca usa un filtro data o un ordinamento su un campo data.

    I campi data del RNDT hanno tutti suffisso ``_dt``: riconoscerli così copre
    anche ``sys_modified_dt`` (ordinamento per indicizzazione), che è proprio il
    caso in cui la nota serve di più.
    """
    sorts_by_date = sort is not None and "_dt" in sort.lower()
    return sorts_by_date or any(v is not None for v in filters)


def _total_count(payload: dict[str, Any]) -> int:
    """Conteggio totale dalla risposta, gestendo il tipo variabile di `total`."""
    total = payload.get("total")
    if isinstance(total, dict):
        return int(total.get("value", 0) or 0)
    return int(total or 0)


_ORG_STOPWORDS = {"di", "del", "della", "dei", "delle", "dell", "de", "la", "il", "lo", "e", "d"}


def _org_probe_token(value: str) -> str | None:
    """Token più distintivo di un nome di ente, per la ricerca esplorativa."""
    tokens = [t.strip("'\"()") for t in value.replace("'", " ").split()]
    candidates = [t for t in tokens if len(t) >= 4 and t.lower() not in _ORG_STOPWORDS]
    if not candidates:
        return None
    return max(candidates, key=len)


def _suggest_orgs(org: str) -> list[str]:
    """Nomi di ente in catalogo che assomigliano a `org` (una sola chiamata).

    L'API ignora `facet`: l'unico modo di scoprire come un ente è scritto in
    catalogo è aggregare a valle un campione di risultati sul token più
    distintivo del nome cercato.
    """
    token = _org_probe_token(org)
    if token is None:
        return []
    try:
        # Passa da `org=` invece di comporre la clausola: il token finisce così
        # tra virgolette con escape, e un nome con punteggiatura riservata
        # (`Emilia-Romagna`, sigle con `:`) non altera la query esplorativa.
        payload = do_search(org=token, num=200, fmt="json")
    except (httpx.HTTPError, ValueError):
        return []
    if not isinstance(payload, dict):
        return []
    return organization_names(payload)[:8]


def _no_results_hint(
    q: str | None,
    bbox: str | None,
    data_category: str | None,
    time: str | None,
    org: str | None = None,
    org_exact: str | None = None,
) -> None:
    """Avviso su stderr per ricerca senza risultati, con suggerimenti contestuali."""
    hints: list[str] = []
    if org_exact:
        hints.append(
            f"--org-exact è un confronto esatto e case-sensitive su {ORG_EXACT_FIELD}: "
            "prova --org, che cerca sul campo analizzato"
        )
    if org:
        suggestions = _suggest_orgs(org)
        exact = next((s for s in suggestions if s.lower() == org.strip().lower()), None)
        if exact is not None:
            hints.append(
                f"l'ente '{exact}' esiste in catalogo: a dare zero è un altro filtro, "
                "rimuovili uno alla volta"
            )
        elif suggestions:
            hints.append("enti simili presenti in catalogo: " + " | ".join(suggestions))
        else:
            hints.append(
                f"nessun ente in catalogo somiglia a '{org}': l'ente potrebbe non "
                "pubblicare sul RNDT (i suoi dati possono essere pubblicati da un "
                "ente sovraordinato). Cerca per territorio con --bbox e "
                "AmbitoTerritoriale_s:Locale"
            )
    if q:
        if ":" in q:
            hints.append(
                "allarga o semplifica il testo di --q (campo:valore richiede il valore "
                "esatto; per i campi _s è case-sensitive)"
            )
        else:
            hints.append(f'allarga il testo di --q o usa wildcard (es. --q "*{q}*")')
    if data_category:
        hints.append("rimuovi --data-category")
    if time:
        hints.append("allarga o rimuovi --time (il periodo può non avere record)")
    if bbox:
        hints.append(
            "allarga o rimuovi --bbox (il filtro è per sovrapposizione; "
            "molti record dichiarano bbox nazionali)"
        )
    if q and ":" not in q:
        hints.append(
            "se cercavi un ente: usa --org (cerca su apiso_OrganizationName_txt, "
            "case-insensitive), oppure cerca per territorio con --bbox e "
            "AmbitoTerritoriale_s:Locale"
        )
    typer.echo("Nessun risultato per la ricerca.", err=True)
    if hints:
        typer.echo("Suggerimenti: " + " ; ".join(hints), err=True)


def _result_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for r in payload.get("results", []) or []:
        bbox = r.get("bbox") or {}
        source = r.get("_source") or {}
        updated, _indexed = record_dates(r)
        rows.append(
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "updated": updated,
                "org": source.get("apiso_OrganizationName_txt"),
                "author": (r.get("author") or {}).get("name"),
                "bbox": (
                    f"{bbox.get('xmin')},{bbox.get('ymin')},{bbox.get('xmax')},{bbox.get('ymax')}"
                    if bbox
                    else None
                ),
            }
        )
    return rows


def _bbox_text(bbox: dict[str, Any]) -> str | None:
    xmin = bbox.get("xmin")
    ymin = bbox.get("ymin")
    xmax = bbox.get("xmax")
    ymax = bbox.get("ymax")
    if not all(isinstance(v, (int, float)) for v in (xmin, ymin, xmax, ymax)):
        return None
    return f"{xmin},{ymin},{xmax},{ymax}"


def _gis_result_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    records_by_id = {
        r.get("id"): r for r in (payload.get("results", []) or []) if isinstance(r, dict) and r.get("id") is not None
    }
    for compact in compact_results(payload):
        record = records_by_id.get(compact.get("id"), {})
        bbox = record.get("bbox") or {}
        rows.append(
            {
                "id": compact.get("id"),
                "title": compact.get("title"),
                "type": compact.get("type"),
                "category": compact.get("category"),
                "org": compact.get("org"),
                "updated": compact.get("updated"),
                "indexed": compact.get("indexed"),
                "resources": ",".join(compact.get("resources") or []),
                "bbox": _bbox_text(bbox),
            }
        )
    return rows


def _resource_url_map(result: dict[str, Any]) -> dict[str, str]:
    resources: dict[str, str] = {}
    for link in (result.get("links") or []):
        if not isinstance(link, dict):
            continue
        href = link.get("href")
        dctype = link.get("dctype")
        if not isinstance(href, str) or not isinstance(dctype, str) or not dctype:
            continue
        key = dctype.upper()
        if key not in resources:
            resources[key] = href
    return resources


def _qgis_result_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    records_by_id = {
        r.get("id"): r for r in (payload.get("results", []) or []) if isinstance(r, dict) and r.get("id") is not None
    }
    for compact in compact_results(payload):
        record = records_by_id.get(compact.get("id"), {})
        bbox = record.get("bbox") or {}
        links = _resource_url_map(record)
        rows.append(
            {
                "id": compact.get("id"),
                "title": compact.get("title"),
                "type": compact.get("type"),
                "category": compact.get("category"),
                "org": compact.get("org"),
                "updated": compact.get("updated"),
                "indexed": compact.get("indexed"),
                "wms_url": links.get("WMS"),
                "wfs_url": links.get("WFS"),
                "download_url": links.get("DOWNLOAD"),
                "xmin": bbox.get("xmin"),
                "ymin": bbox.get("ymin"),
                "xmax": bbox.get("xmax"),
                "ymax": bbox.get("ymax"),
            }
        )
    return rows


def _bbox_feature(result: dict[str, Any]) -> dict[str, Any] | None:
    bbox = result.get("bbox") or {}
    xmin = bbox.get("xmin")
    ymin = bbox.get("ymin")
    xmax = bbox.get("xmax")
    ymax = bbox.get("ymax")
    if not all(isinstance(v, (int, float)) for v in (xmin, ymin, xmax, ymax)):
        return None
    source = result.get("_source") or {}
    updated, indexed = record_dates(result)
    compact = {
        "id": result.get("id"),
        "title": result.get("title"),
        "org": source.get("apiso_OrganizationName_txt") or (result.get("author") or {}).get("name"),
        "type": source.get("apiso_Type_s"),
        "updated": updated,
        "indexed": indexed,
        "resources": sorted(_resource_url_map(result).keys()),
    }
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [xmin, ymin],
                    [xmax, ymin],
                    [xmax, ymax],
                    [xmin, ymax],
                    [xmin, ymin],
                ]
            ],
        },
        "properties": compact,
    }


@app.command()
def search(
    q: str | None = typer.Option(None, "--q", "-q", help="Testo di ricerca (Lucene/Elasticsearch)."),
    bbox: str | None = typer.Option(None, "--bbox", help="Bounding box WGS84 xmin,ymin,xmax,ymax."),
    bbox_crs: str | None = typer.Option(
        None,
        "--bbox-crs",
        help="CRS della bbox. Supportati: EPSG:4326 (default implicito), CRS:84, WGS84.",
    ),
    org: str | None = typer.Option(
        None,
        "--org",
        help=(
            "Ente responsabile: frase su apiso_OrganizationName_txt (case-insensitive, "
            'es. --org "comune di torino"). In AND con gli altri filtri.'
        ),
    ),
    org_exact: str | None = typer.Option(
        None,
        "--org-exact",
        help=(
            "Ente responsabile in forma esatta e case-sensitive su EnteResponsabile_s "
            '(es. --org-exact "Comune di Torino"). Alternativo a --org.'
        ),
    ),
    data_category: str | None = typer.Option(
        None,
        "--data-category",
        "-c",
        help="Categoria tematica ISO 19115 (es. planningCadastre). Vedi `discover`.",
    ),
    time: str | None = typer.Option(None, "--time", help="Intervallo temporale della risorsa yyyy-mm-dd/yyyy-mm-dd."),
    modified: str | None = typer.Option(None, "--modified", help="Intervallo modifica record nel catalogo yyyy-mm-dd/yyyy-mm-dd."),
    updated_from: str | None = typer.Option(
        None,
        "--updated-from",
        help="Filtra per data minima di aggiornamento metadato (yyyy-mm-dd, campo apiso_Modified_dt).",
    ),
    updated_to: str | None = typer.Option(
        None,
        "--updated-to",
        help="Filtra per data massima di aggiornamento metadato (yyyy-mm-dd, campo apiso_Modified_dt).",
    ),
    published_from: str | None = typer.Option(
        None,
        "--published-from",
        help="Filtra per data minima di pubblicazione (yyyy-mm-dd, campo apiso_PublicationDate_dt).",
    ),
    published_to: str | None = typer.Option(
        None,
        "--published-to",
        help="Filtra per data massima di pubblicazione (yyyy-mm-dd, campo apiso_PublicationDate_dt).",
    ),
    sort: str | None = typer.Option(
        None,
        "--sort",
        help=(
            "Ordinamento 'campo:asc|desc' su campo sortable (es. apiso_Modified_dt:desc). "
            "Attenzione: 'dateDescending'/'dateAscending' NON ordinano su RNDT. "
            "Vedi `discover --what sort_values`."
        ),
    ),
    start: int = typer.Option(1, "--start", help="Indice 1-based del primo record."),
    num: int = typer.Option(10, "--num", "-n", help="Numero massimo di record (max 5000)."),
    item_id: str | None = typer.Option(None, "--id", help="ID metadato specifico."),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help=(
            "Preset colonne per output table/csv: default | gis | qgis. "
            "Se `--format` non è indicato, attiva da solo l'output table."
        ),
        case_sensitive=False,
    ),
) -> None:
    """Cerca metadati nel RNDT."""
    profile_given = profile is not None
    profile = (profile or "default").lower()
    if profile not in {"default", "gis", "qgis"}:
        typer.echo("Profilo non supportato: usare `default`, `gis` oppure `qgis`.", err=True)
        raise typer.Exit(2)
    if profile_given:
        if not output.is_mode_explicit():
            output.set_mode("table")
        elif output.get_mode() in {"json", "compact"}:
            typer.echo(
                f"Avviso: --profile è ignorato con --format {output.get_mode()} "
                "(i preset di colonne valgono solo per table e csv).",
                err=True,
            )
    try:
        payload = do_search(
            q=q,
            bbox=bbox,
            bbox_crs=bbox_crs,
            org=org,
            org_exact=org_exact,
            data_category=data_category,
            time=time,
            modified=modified,
            updated_from=updated_from,
            updated_to=updated_to,
            published_from=published_from,
            published_to=published_to,
            sort=sort,
            start=start,
            num=num,
            fmt="json",
            item_id=item_id,
        )
    except json.JSONDecodeError:
        typer.echo("Risposta RNDT inattesa (JSON non valido).", err=True)
        raise typer.Exit(1)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)
    except httpx.HTTPError as exc:
        _http_error(exc, sort=sort)
    if not isinstance(payload, dict):
        typer.echo("Risposta RNDT inattesa (non è un oggetto JSON).", err=True)
        raise typer.Exit(1)
    zero = _total_count(payload) == 0
    mode = output.get_mode()
    if mode == "json":
        output.emit(payload)
        if zero:
            _no_results_hint(q, bbox, data_category, time, org, org_exact)
        elif _uses_date_filters(sort, modified, updated_from, updated_to, published_from, published_to, time):
            typer.echo(_RAW_DATE_NOTE, err=True)
        return
    if mode == "compact":
        rows = compact_results(payload)
        if not rows:
            _no_results_hint(q, bbox, data_category, time, org, org_exact)
            return
        output.emit(payload, table_rows=rows)
        return
    if profile == "gis":
        rows = _gis_result_rows(payload)
    elif profile == "qgis":
        rows = _qgis_result_rows(payload)
    else:
        rows = _result_rows(payload)
    if not rows:
        _no_results_hint(q, bbox, data_category, time, org, org_exact)
        return
    title = f"RNDT — {payload.get('num', len(rows))} di {payload.get('total', '?')}"
    caption = _table_date_caption(rows[0])
    output.emit(payload, table_rows=rows, table_title=title, table_caption=caption)


@app.command()
def footprints(
    q: str | None = typer.Option(None, "--q", "-q", help="Testo di ricerca (Lucene/Elasticsearch)."),
    bbox: str | None = typer.Option(None, "--bbox", help="Bounding box WGS84 xmin,ymin,xmax,ymax."),
    bbox_crs: str | None = typer.Option(
        None,
        "--bbox-crs",
        help="CRS della bbox. Supportati: EPSG:4326 (default implicito), CRS:84, WGS84.",
    ),
    org: str | None = typer.Option(
        None,
        "--org",
        help=(
            "Ente responsabile: frase su apiso_OrganizationName_txt (case-insensitive, "
            'es. --org "comune di torino"). In AND con gli altri filtri.'
        ),
    ),
    org_exact: str | None = typer.Option(
        None,
        "--org-exact",
        help=(
            "Ente responsabile in forma esatta e case-sensitive su EnteResponsabile_s "
            '(es. --org-exact "Comune di Torino"). Alternativo a --org.'
        ),
    ),
    data_category: str | None = typer.Option(
        None,
        "--data-category",
        "-c",
        help="Categoria tematica ISO 19115 (es. planningCadastre). Vedi `discover`.",
    ),
    time: str | None = typer.Option(None, "--time", help="Intervallo temporale della risorsa yyyy-mm-dd/yyyy-mm-dd."),
    modified: str | None = typer.Option(None, "--modified", help="Intervallo modifica record nel catalogo yyyy-mm-dd/yyyy-mm-dd."),
    updated_from: str | None = typer.Option(
        None,
        "--updated-from",
        help="Filtra per data minima di aggiornamento metadato (yyyy-mm-dd, campo apiso_Modified_dt).",
    ),
    updated_to: str | None = typer.Option(
        None,
        "--updated-to",
        help="Filtra per data massima di aggiornamento metadato (yyyy-mm-dd, campo apiso_Modified_dt).",
    ),
    published_from: str | None = typer.Option(
        None,
        "--published-from",
        help="Filtra per data minima di pubblicazione (yyyy-mm-dd, campo apiso_PublicationDate_dt).",
    ),
    published_to: str | None = typer.Option(
        None,
        "--published-to",
        help="Filtra per data massima di pubblicazione (yyyy-mm-dd, campo apiso_PublicationDate_dt).",
    ),
    sort: str | None = typer.Option(
        None,
        "--sort",
        help=(
            "Ordinamento 'campo:asc|desc' su campo sortable (es. apiso_Modified_dt:desc). "
            "Attenzione: 'dateDescending'/'dateAscending' NON ordinano su RNDT. "
            "Vedi `discover --what sort_values`."
        ),
    ),
    start: int = typer.Option(1, "--start", help="Indice 1-based del primo record."),
    num: int = typer.Option(10, "--num", "-n", help="Numero massimo di record (max 5000)."),
) -> None:
    """Esporta footprint bbox come GeoJSON FeatureCollection (EPSG:4326)."""
    try:
        payload = do_search(
            q=q,
            bbox=bbox,
            bbox_crs=bbox_crs,
            org=org,
            org_exact=org_exact,
            data_category=data_category,
            time=time,
            modified=modified,
            updated_from=updated_from,
            updated_to=updated_to,
            published_from=published_from,
            published_to=published_to,
            sort=sort,
            start=start,
            num=num,
            fmt="json",
            item_id=None,
        )
    except json.JSONDecodeError:
        typer.echo("Risposta RNDT inattesa (JSON non valido).", err=True)
        raise typer.Exit(1)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)
    except httpx.HTTPError as exc:
        _http_error(exc, sort=sort)

    if not isinstance(payload, dict):
        typer.echo("Risposta RNDT inattesa (non è un oggetto JSON).", err=True)
        raise typer.Exit(1)

    features: list[dict[str, Any]] = []
    for result in cast(list[dict[str, Any]], payload.get("results", []) or []):
        feature = _bbox_feature(result)
        if feature is not None:
            features.append(feature)
    geojson: dict[str, Any] = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": features,
        "meta": {
            "total_results": payload.get("total"),
            "features_with_bbox": len(features),
            "start": payload.get("start"),
            "num": payload.get("num"),
        },
    }
    output.emit(geojson)
    if _total_count(payload) == 0:
        _no_results_hint(q, bbox, data_category, time, org, org_exact)


@app.command()
def get(
    item_id: str = typer.Argument(..., help="ID del metadato (es. age:D_E973_MARSAGLIA)."),
    as_xml: bool = typer.Option(False, "--xml", help="Restituisci XML ISO 19139 grezzo."),
    as_html: bool = typer.Option(False, "--html", help="Restituisci HTML."),
) -> None:
    """Recupera il dettaglio di un singolo metadato."""
    if as_xml and as_html:
        raise typer.BadParameter("Specifica --xml oppure --html, non entrambi.")
    if not (as_xml or as_html) and output.get_mode() in {"csv", "compact"}:
        typer.echo(
            "Il dettaglio di un metadato non è tabellare: usa --format json (default) o table.",
            err=True,
        )
        raise typer.Exit(1)
    try:
        if as_xml:
            output.emit_text(get_item_xml(item_id))
            return
        if as_html:
            output.emit_text(get_item_html(item_id))
            return
        payload = get_item(item_id)
    except ItemNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    except json.JSONDecodeError:
        typer.echo("Risposta RNDT inattesa (JSON non valido).", err=True)
        raise typer.Exit(1)
    except httpx.HTTPError as exc:
        _http_error(exc)
    output.emit(payload)


@app.command()
def resources(
    item_ids: list[str] = typer.Argument(
        ...,
        help="ID di uno o più metadati (es. age:D_E973_MARSAGLIA). Più ID = health-check in batch.",
    ),
    check: bool = typer.Option(
        True,
        "--check/--no-check",
        help="Verifica la raggiungibilità HTTP di ogni endpoint trovato.",
    ),
) -> None:
    """Estrae risorse fruibili (WMS/WFS/download) e, opzionalmente, le verifica."""
    batch = len(item_ids) > 1
    entries: list[dict[str, Any]] = []
    for item_id in item_ids:
        entry: dict[str, Any] = {"id": item_id}
        try:
            payload = get_item(item_id)
        except ItemNotFoundError as exc:
            entry["error"] = str(exc)
            entries.append(entry)
            continue
        except json.JSONDecodeError:
            entry["error"] = "Risposta RNDT inattesa (JSON non valido)."
            entries.append(entry)
            continue
        except httpx.HTTPError as exc:
            if batch:
                if isinstance(exc, httpx.HTTPStatusError):
                    entry["error"] = f"Errore HTTP {exc.response.status_code}"
                else:
                    entry["error"] = f"Errore di rete ({type(exc).__name__})"
                entries.append(entry)
                continue
            _http_error(exc)

        rows = extract_resources(payload)
        if check:
            rows_checked = check_resources(rows)
        else:
            rows_checked = rows
        entry["count"] = len(rows_checked)
        entry["checked"] = check
        entry["resources"] = rows_checked
        entries.append(entry)

    if not batch:
        # Formato storico: il payload del singolo metadato al primo livello.
        entry = entries[0]
        if "error" in entry:
            typer.echo(entry["error"], err=True)
            raise typer.Exit(1)
        response = dict(entry)
        mode = output.get_mode()
        if mode == "json":
            output.emit(response)
            return
        if not response.get("resources"):
            typer.echo("Nessuna risorsa fruibile trovata per il metadato.", err=True)
            return
        output.emit(response, table_rows=response["resources"], table_title=f"RNDT resources — {item_ids[0]}")
        return

    mode = output.get_mode()
    if mode == "json":
        output.emit({"count": len(entries), "checked": check, "results": entries})
        return
    rows_all: list[dict[str, Any]] = []
    for entry in entries:
        if "error" in entry:
            rows_all.append({"id": entry["id"], "error": entry["error"]})
            continue
        for r in entry.get("resources") or []:
            rows_all.append({"id": entry["id"], **r})
    if not rows_all:
        typer.echo("Nessuna risorsa fruibile trovata.", err=True)
        return
    output.emit(
        {"count": len(entries), "checked": check, "results": entries},
        table_rows=rows_all,
        table_title=f"RNDT resources — {len(entries)} metadati",
    )


@app.command()
def discover(
    what: str = typer.Option(
        "all",
        "--what",
        help="Sezione: all|data_categories|sort_values|output_formats|search_params|lucene_fields.",
    ),
) -> None:
    """Codelist e parametri validi (nessuna chiamata di rete)."""
    full = codelists.codelist_payload()
    if what == "all":
        if output.get_mode() == "json":
            output.emit(full)
        else:
            for section, table in full.items():
                rows = [{"value": k, "description": v} for k, v in table.items()]
                output.emit(table, table_rows=rows, table_title=section)
        return
    if what not in full:
        raise typer.BadParameter(
            f"Sezione sconosciuta: {what}. Disponibili: {', '.join(['all', *full.keys()])}."
        )
    values = full[what]
    if output.get_mode() == "json":
        output.emit(values)
    else:
        rows = [{"value": k, "description": v} for k, v in values.items()]
        output.emit(values, table_rows=rows, table_title=what)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
