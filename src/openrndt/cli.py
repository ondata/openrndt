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
from openrndt.search import compact_results
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


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"openrndt {__version__}")
        raise typer.Exit(0)


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
    fmt: str = typer.Option(
        "json",
        "--format",
        "-F",
        help="Formato di output: json (default), table, csv, compact (NDJSON per agenti, solo per search).",
        case_sensitive=False,
    ),
) -> None:
    config.set_base_url(base_url)
    config.set_timeout(timeout)
    try:
        output.set_mode(fmt.lower())
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)


def _http_error(exc: httpx.HTTPError) -> NoReturn:
    """Stampa un messaggio leggibile su stderr ed esce 1 — mai uno stack trace.

    Distingue una risposta HTTP di errore (status) da un problema di rete
    (connessione rifiutata, timeout dopo i retry, DNS): in entrambi i casi
    l'agente che orchestra la CLI deve capire l'esito dal solo output.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        typer.echo(f"Errore HTTP {exc.response.status_code}: {exc.request.url}", err=True)
    else:
        url = getattr(getattr(exc, "request", None), "url", None) or config.get_base_url()
        typer.echo(
            f"Errore di rete: impossibile contattare {url} ({type(exc).__name__}).",
            err=True,
        )
    raise typer.Exit(1)


def _result_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for r in payload.get("results", []) or []:
        bbox = r.get("bbox") or {}
        rows.append(
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "updated": r.get("updated"),
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
    compact = {
        "id": result.get("id"),
        "title": result.get("title"),
        "org": source.get("apiso_OrganizationName_txt") or (result.get("author") or {}).get("name"),
        "type": source.get("apiso_Type_s"),
        "updated": result.get("updated"),
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
    profile: str = typer.Option(
        "default",
        "--profile",
        help="Preset colonne per output table/csv: default | gis | qgis.",
        case_sensitive=False,
    ),
) -> None:
    """Cerca metadati nel RNDT."""
    profile = profile.lower()
    if profile not in {"default", "gis", "qgis"}:
        typer.echo("Profilo non supportato: usare `default`, `gis` oppure `qgis`.", err=True)
        raise typer.Exit(2)
    try:
        payload = do_search(
            q=q,
            bbox=bbox,
            bbox_crs=bbox_crs,
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
        _http_error(exc)
    if not isinstance(payload, dict):
        typer.echo("Risposta RNDT inattesa (non è un oggetto JSON).", err=True)
        raise typer.Exit(1)
    mode = output.get_mode()
    if mode == "json":
        output.emit(payload)
        return
    if mode == "compact":
        rows = compact_results(payload)
        if not rows:
            typer.echo("Nessun risultato per la ricerca.", err=True)
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
        typer.echo("Nessun risultato per la ricerca.", err=True)
        return
    title = f"RNDT — {payload.get('num', len(rows))} di {payload.get('total', '?')}"
    output.emit(payload, table_rows=rows, table_title=title)


@app.command()
def footprints(
    q: str | None = typer.Option(None, "--q", "-q", help="Testo di ricerca (Lucene/Elasticsearch)."),
    bbox: str | None = typer.Option(None, "--bbox", help="Bounding box WGS84 xmin,ymin,xmax,ymax."),
    bbox_crs: str | None = typer.Option(
        None,
        "--bbox-crs",
        help="CRS della bbox. Supportati: EPSG:4326 (default implicito), CRS:84, WGS84.",
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
        _http_error(exc)

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
    item_id: str = typer.Argument(..., help="ID del metadato (es. age:D_E973_MARSAGLIA)."),
    check: bool = typer.Option(
        True,
        "--check/--no-check",
        help="Verifica la raggiungibilità HTTP di ogni endpoint trovato.",
    ),
) -> None:
    """Estrae risorse fruibili (WMS/WFS/download) e, opzionalmente, le verifica."""
    try:
        payload = get_item(item_id)
    except ItemNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    except json.JSONDecodeError:
        typer.echo("Risposta RNDT inattesa (JSON non valido).", err=True)
        raise typer.Exit(1)
    except httpx.HTTPError as exc:
        _http_error(exc)

    rows = extract_resources(payload)
    if check:
        rows_checked = check_resources(rows)
    else:
        rows_checked = rows

    response: dict[str, Any] = {
        "id": item_id,
        "count": len(rows_checked),
        "checked": check,
        "resources": rows_checked,
    }
    mode = output.get_mode()
    if mode == "json":
        output.emit(response)
        return
    if not rows_checked:
        typer.echo("Nessuna risorsa fruibile trovata per il metadato.", err=True)
        return
    output.emit(response, table_rows=rows_checked, table_title=f"RNDT resources — {item_id}")


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
