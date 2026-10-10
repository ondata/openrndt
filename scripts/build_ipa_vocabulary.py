"""Rigenera `src/openrndt/data/ipa.json`, il vocabolario dei codici IPA presenti nel RNDT (#38), e la copia dell'anagrafica IPA nel pacchetto (#44).

Il prefisso dell'id di ogni scheda è il codice IPA dell'ente titolare. Lo script
scorre l'intero catalogo (circa 24.000 schede, 5 minuti, 1,2 GB: ogni risposta
porta l'XML della scheda), conta le schede per prefisso in minuscolo e ci
aggiunge nome, acronimo e categoria dall'anagrafica IPA verificata che il workflow
`ipa-registry.yml` pubblica ogni mese nella release `data-ipa`. La stessa
anagrafica va nel pacchetto, compressa (`ipa-enti.csv.gz`), per gli enti che non
hanno schede nel RNDT.

Da lanciare prima di ogni release:

    uv run python scripts/build_ipa_vocabulary.py

Con `--scan prefissi.csv` riusa una scansione già fatta (colonne id, prefisso, ente)
e con `--save-scan` salva quella nuova; con `--registry ipa-enti.csv` usa una copia
locale dell'anagrafica (da `scripts/build_ipa_registry.py`). L'anagrafica deve
avere le colonne della #44, con la categoria.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import httpx

SEARCH = "https://geodati.gov.it/RNDT/rest/metadata/search"
REGISTRY = "https://github.com/ondata/openrndt/releases/download/data-ipa/ipa-enti.csv"
PAGE = 500
OUT = Path(__file__).resolve().parent.parent / "src" / "openrndt" / "data" / "ipa.json"
REGISTRY_OUT = OUT.with_name("ipa-enti.csv.gz")
REGISTRY_COLUMNS = ["codice_ipa", "denominazione", "acronimo", "categoria", "nome_categoria"]
UA = {"User-Agent": "openrndt-build-ipa (+https://github.com/ondata/openrndt)"}


def scan(client: httpx.Client) -> list[tuple[str, str, str]]:
    """Id, prefisso ed ente responsabile di ogni scheda del catalogo."""
    rows: list[tuple[str, str, str]] = []
    start, total = 1, None
    t0 = time.time()
    while total is None or start <= total:
        for attempt in range(5):
            try:
                r = client.get(SEARCH, params={"q": "*:*", "num": PAGE, "start": start, "f": "json", "sort": "title:asc"})
                r.raise_for_status()
                break
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                print(f"pagina {start}, tentativo {attempt + 1}: {exc!r}", file=sys.stderr)
                time.sleep(10 * (attempt + 1))
        else:
            raise SystemExit(f"pagina {start} non letta dopo 5 tentativi")
        data = r.json()
        total = data["total"]["value"] if isinstance(data["total"], dict) else data["total"]
        for res in data.get("results", []):
            ident = res.get("id") or ""
            rows.append((ident, ident.split(":")[0], (res.get("_source") or {}).get("EnteResponsabile_s") or ""))
        print(f"{min(start + PAGE - 1, total)} di {total}, {time.time() - t0:.0f}s", file=sys.stderr)
        start += PAGE
    if len({r[0] for r in rows}) != total:
        raise SystemExit(f"schede distinte {len({r[0] for r in rows})} su {total}: paginazione non affidabile")
    return rows


def registry_text(client: httpx.Client, path: Path | None) -> str:
    """L'anagrafica della release `data-ipa`, o di `path`, con le colonne di `build_ipa_registry.py`."""
    if path:
        text = path.read_text(encoding="utf-8")
    else:
        r = client.get(REGISTRY, follow_redirects=True)
        r.raise_for_status()
        text = r.content.decode("utf-8")
    # La release ha i CRLF di `csv.writer`, una copia letta con `read_text` no: stessi byte nel gzip.
    text = text.replace("\r\n", "\n")
    header = text.split("\n", 1)[0].strip().split(",")
    if header != REGISTRY_COLUMNS:
        raise SystemExit(f"anagrafica IPA con colonne {header}, attese {REGISTRY_COLUMNS}: rilanciare il workflow ipa-registry")
    return text


def ipa_registry(text: str) -> dict[str, dict[str, str]]:
    """Codice IPA → riga dell'anagrafica."""
    return {row["codice_ipa"]: row for row in csv.DictReader(io.StringIO(text))}


def build(rows: list[tuple[str, str, str]], ipa: dict[str, dict[str, str]]) -> dict:
    count: Counter[str] = Counter()
    spellings: dict[str, set[str]] = defaultdict(set)
    enti: dict[str, Counter[str]] = defaultdict(Counter)
    for _, prefix, ente in rows:
        code = prefix.lower()
        count[code] += 1
        spellings[code].add(prefix)
        if ente:
            enti[code][ente] += 1
    codes = []
    for code, n in sorted(count.items(), key=lambda kv: (-kv[1], kv[0])):
        entry = ipa.get(code, {})
        codes.append({
            "codice": code,
            "ipa": code in ipa,
            "nome_ipa": entry.get("denominazione") or None,
            "acronimo": entry.get("acronimo") or None,
            "categoria": entry.get("categoria") or None,
            "nome_categoria": entry.get("nome_categoria") or None,
            "enti": [e for e, _ in enti[code].most_common()],
            "schede": n,
            "grafie": sorted(spellings[code]),
        })
    return {"generato": date.today().isoformat(), "schede": len(rows), "codici": codes}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scan", type=Path, help="CSV di una scansione già fatta (id, prefisso, ente)")
    parser.add_argument("--save-scan", type=Path, help="dove salvare la scansione nuova")
    parser.add_argument("--registry", type=Path, help="copia locale dell'anagrafica IPA (da scripts/build_ipa_registry.py)")
    args = parser.parse_args()
    with httpx.Client(timeout=120, headers=UA) as client:
        if args.scan:
            with args.scan.open(encoding="utf-8") as f:
                rows = [(r["id"], r["prefisso"], r["ente"]) for r in csv.DictReader(f)]
        else:
            rows = scan(client)
            if args.save_scan:
                with args.save_scan.open("w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(["id", "prefisso", "ente"])
                    w.writerows(rows)
        text = registry_text(client, args.registry)
        vocabulary = build(rows, ipa_registry(text))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(vocabulary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # mtime=0: lo stesso file dà lo stesso gzip, e il diff resta vuoto se l'anagrafica non cambia.
    REGISTRY_OUT.write_bytes(gzip.compress(text.encode("utf-8"), compresslevel=9, mtime=0))
    valid = sum(c["ipa"] for c in vocabulary["codici"])
    print(f"{OUT}: {len(vocabulary['codici'])} codici ({valid} nell'Indice PA), {vocabulary['schede']} schede")
    print(f"{REGISTRY_OUT}: {text.count(chr(10)) - 1} enti, {REGISTRY_OUT.stat().st_size} byte")


if __name__ == "__main__":
    main()
