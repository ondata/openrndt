"""CLI Typer di openrndt — 3 comandi MVP: search, get, discover."""

from __future__ import annotations

from typing import Any

import httpx
import typer

from openrndt import codelists, config, output
from openrndt.item import ItemNotFoundError, get_item, get_item_html, get_item_xml
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


@app.callback()
def _root(
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        help=f"Override del base URL RNDT (default: env {config.ENV_BASE_URL} o {config.DEFAULT_BASE_URL}).",
    ),
    fmt: str = typer.Option(
        "json",
        "--format",
        "-F",
        help="Formato di output: json (default), table, csv.",
        case_sensitive=False,
    ),
) -> None:
    config.set_base_url(base_url)
    output.set_mode(fmt.lower())


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


@app.command()
def search(
    q: str | None = typer.Option(None, "--q", "-q", help="Testo di ricerca (Lucene/Elasticsearch)."),
    bbox: str | None = typer.Option(None, "--bbox", help="Bounding box WGS84 xmin,ymin,xmax,ymax."),
    data_category: str | None = typer.Option(
        None,
        "--data-category",
        "-c",
        help="Categoria tematica ISO 19115 (es. planningCadastre). Vedi `discover`.",
    ),
    time: str | None = typer.Option(None, "--time", help="Intervallo temporale della risorsa yyyy-mm-dd/yyyy-mm-dd."),
    modified: str | None = typer.Option(None, "--modified", help="Intervallo modifica record nel catalogo yyyy-mm-dd/yyyy-mm-dd."),
    sort: str | None = typer.Option(None, "--sort", help="Ordinamento (dateDescending|dateAscending|relevance|title[:desc])."),
    start: int = typer.Option(1, "--start", help="Indice 1-based del primo record."),
    num: int = typer.Option(10, "--num", "-n", help="Numero massimo di record (max 5000)."),
    item_id: str | None = typer.Option(None, "--id", help="ID metadato specifico."),
) -> None:
    """Cerca metadati nel RNDT."""
    try:
        payload = do_search(
            q=q,
            bbox=bbox,
            data_category=data_category,
            time=time,
            modified=modified,
            sort=sort,
            start=start,
            num=num,
            fmt="json",
            item_id=item_id,
        )
    except httpx.HTTPStatusError as exc:
        typer.echo(f"Errore HTTP {exc.response.status_code}: {exc.request.url}", err=True)
        raise typer.Exit(1)
    if not isinstance(payload, dict):
        raise typer.Exit(1)
    if output.get_mode() == "json":
        output.emit(payload)
    else:
        rows = _result_rows(payload)
        title = f"RNDT — {payload.get('num', len(rows))} di {payload.get('total', '?')}"
        output.emit(payload, table_rows=rows, table_title=title)


@app.command()
def get(
    item_id: str = typer.Argument(..., help="ID del metadato (es. age:D_E973_MARSAGLIA)."),
    as_xml: bool = typer.Option(False, "--xml", help="Restituisci XML ISO 19139 grezzo."),
    as_html: bool = typer.Option(False, "--html", help="Restituisci HTML."),
) -> None:
    """Recupera il dettaglio di un singolo metadato."""
    if as_xml and as_html:
        raise typer.BadParameter("Specifica --xml oppure --html, non entrambi.")
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
    except httpx.HTTPStatusError as exc:
        typer.echo(f"Errore HTTP {exc.response.status_code}: {exc.request.url}", err=True)
        raise typer.Exit(1)
    output.emit(payload)


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
    section = full[what]
    if output.get_mode() == "json":
        output.emit(section)
    else:
        rows = [{"value": k, "description": v} for k, v in section.items()]
        output.emit(section, table_rows=rows, table_title=what)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
