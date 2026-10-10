"""Scarica l'anagrafica degli enti dall'Indice PA e la riduce a codice, nome, acronimo e categoria (#38, #44).

Il file esce ordinato per codice IPA in minuscolo, con le colonne
`codice_ipa,denominazione,acronimo,categoria,nome_categoria`. Il nome della
categoria viene dal dataset `categorie-enti`, che dà anche la tipologia
(Pubbliche Amministrazioni, Gestori di Pubblici Servizi, ...): non serve tenerla.
Prima di scriverlo lo script lo verifica: intestazione attesa, almeno
`--min-rows` enti, codici non vuoti, distinti e fatti solo di lettere, cifre e
`_`, ogni ente con una categoria che ha un nome. Se una verifica fallisce esce con errore e non
scrive nulla, così il workflow mensile non sostituisce la copia buona.

    uv run python scripts/build_ipa_registry.py ipa-enti.csv
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path

import httpx

IPA_CSV = "https://www.indicepa.gov.it/ipa-dati/datastore/dump/d09adf99-dc10-4349-8c53-27b1e5aa97b6?bom=True"
CATEGORIES_CSV = "https://www.indicepa.gov.it/ipa-dati/datastore/dump/84ebb2e7-0e61-427b-a1dd-ab8bb2a84f07?bom=True"
COLUMNS = ["codice_ipa", "denominazione", "acronimo", "categoria", "nome_categoria"]
CODE_RE = re.compile(r"^[a-z0-9_]+$")


def download(url: str) -> str:
    with httpx.Client(timeout=120, follow_redirects=True, headers={"User-Agent": "openrndt-ipa-registry (+https://github.com/ondata/openrndt)"}) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.content.decode("utf-8-sig")


def _reader(text: str, columns: set[str], what: str) -> csv.DictReader:
    reader = csv.DictReader(io.StringIO(text))
    missing = columns - set(reader.fieldnames or [])
    if missing:
        raise SystemExit(f"colonne mancanti in {what}: {', '.join(sorted(missing))}")
    return reader


def categories(text: str) -> dict[str, str]:
    """Codice categoria → nome, dal dataset `categorie-enti` (53 il 2026-10-10)."""
    reader = _reader(text, {"Codice_categoria", "Nome_categoria"}, "categorie-enti")
    return {(row["Codice_categoria"] or "").strip(): (row["Nome_categoria"] or "").strip() for row in reader}


def reduce(text: str, names: dict[str, str]) -> list[list[str]]:
    reader = _reader(text, {"Codice_IPA", "Denominazione_ente", "Acronimo", "Codice_Categoria"}, "anagrafica IPA")
    rows = []
    for row in reader:
        category = (row["Codice_Categoria"] or "").strip()
        rows.append([
            (row["Codice_IPA"] or "").strip().lower(),
            (row["Denominazione_ente"] or "").strip(),
            (row["Acronimo"] or "").strip(),
            category,
            names.get(category, ""),
        ])
    return sorted(rows, key=lambda r: r[0])


def verify(rows: list[list[str]], min_rows: int) -> None:
    problems = []
    if len(rows) < min_rows:
        problems.append(f"{len(rows)} enti, meno di {min_rows}")
    bad = [r[0] for r in rows if not CODE_RE.match(r[0])]
    if bad:
        problems.append(f"{len(bad)} codici non validi, es. {bad[:3]}")
    codes = [r[0] for r in rows]
    if len(set(codes)) != len(codes):
        problems.append(f"{len(codes) - len(set(codes))} codici ripetuti")
    if any(not r[1] for r in rows):
        problems.append("enti senza denominazione")
    unnamed = sorted({r[3] for r in rows if not r[4]})
    if unnamed:
        problems.append(f"categorie senza nome in categorie-enti: {unnamed[:5]}")
    if problems:
        raise SystemExit("anagrafica IPA non valida: " + "; ".join(problems))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path, help="CSV da scrivere")
    parser.add_argument("--min-rows", type=int, default=20000, help="numero minimo di enti (23.757 il 2026-10-10)")
    args = parser.parse_args()
    rows = reduce(download(IPA_CSV), categories(download(CATEGORIES_CSV)))
    verify(rows, args.min_rows)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(rows)
    print(f"{args.out}: {len(rows)} enti, {sum(1 for r in rows if r[2])} con acronimo, {len({r[3] for r in rows})} categorie", file=sys.stderr)


if __name__ == "__main__":
    main()
