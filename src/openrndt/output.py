"""Output dispatcher: json | table | csv | compact."""

from __future__ import annotations

import csv
import io
import json
import sys
from typing import Any, Iterable

from rich.console import Console
from rich.table import Table

_output_mode: str = "json"
_mode_explicit: bool = False
_console = Console()


def set_mode(mode: str, *, explicit: bool = True) -> None:
    """Imposta il formato corrente.

    `explicit=False` marca il formato come valore di default (nessun `--format`
    da riga di comando): i comandi possono allora sceglierne uno più adatto.
    """
    global _output_mode, _mode_explicit
    if mode not in {"json", "table", "csv", "compact"}:
        raise ValueError(f"Formato non supportato: {mode}")
    _output_mode = mode
    _mode_explicit = explicit


def get_mode() -> str:
    return _output_mode


def is_mode_explicit() -> bool:
    """True se il formato corrente è stato richiesto esplicitamente."""
    return _mode_explicit


def emit(data: Any, *, table_rows: Iterable[dict[str, Any]] | None = None, table_title: str | None = None) -> None:
    """Stampa `data` rispettando il formato corrente.

    - `json`: serializza `data` con indentazione.
    - `table`: usa `table_rows` (lista di dict piatti) se fornita, altrimenti pretty-print del JSON.
    - `csv`: scrive `table_rows` se fornita, altrimenti output vuoto.
    - `compact`: scrive `table_rows` come NDJSON (una riga JSON per record).
    """
    if _output_mode == "json":
        sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        return

    if _output_mode == "compact":
        rows = list(table_rows) if table_rows is not None else []
        for row in rows:
            sys.stdout.write(json.dumps(row, ensure_ascii=False) + "\n")
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
