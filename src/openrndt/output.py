"""Output dispatcher: json | table | csv."""

from __future__ import annotations

import csv
import io
import json
import sys
from typing import Any, Iterable

from rich.console import Console
from rich.table import Table

_output_mode: str = "json"
_console = Console()


def set_mode(mode: str) -> None:
    global _output_mode
    if mode not in {"json", "table", "csv"}:
        raise ValueError(f"Formato non supportato: {mode}")
    _output_mode = mode


def get_mode() -> str:
    return _output_mode


def emit(data: Any, *, table_rows: Iterable[dict[str, Any]] | None = None, table_title: str | None = None) -> None:
    """Stampa `data` rispettando il formato corrente.

    - `json`: serializza `data` con indentazione.
    - `table`: usa `table_rows` (lista di dict piatti) se fornita, altrimenti pretty-print del JSON.
    - `csv`: scrive `table_rows` se fornita, altrimenti errore.
    """
    if _output_mode == "json":
        sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        return

    if _output_mode == "table":
        if table_rows is None:
            _console.print_json(data=data)
            return
        rows = list(table_rows)
        if not rows:
            _console.print("[dim]nessun risultato[/dim]")
            return
        table = Table(title=table_title, show_lines=False)
        for key in rows[0].keys():
            table.add_column(key, overflow="fold")
        for row in rows:
            table.add_row(*[str(v) if v is not None else "" for v in row.values()])
        _console.print(table)
        return

    if _output_mode == "csv":
        rows = list(table_rows) if table_rows is not None else []
        if not rows:
            sys.stdout.write("")
            return
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        sys.stdout.write(buf.getvalue())
        return


def emit_text(text: str) -> None:
    """Scrive testo grezzo (XML/HTML/CSV) su stdout — bypassa il dispatcher."""
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
