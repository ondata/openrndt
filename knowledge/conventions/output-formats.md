---
type: Convention
title: Formati di output
description: I quattro formati della CLI (json, table, csv, compact) e i criteri di scelta.
tags: [output, json, ndjson, csv]
timestamp: 2026-07-17T00:00:00Z
---

Il formato si sceglie con l'opzione globale `--format`/`-F`, **prima** del comando. Il dispatcher è `output.py`.

# Formati

| Formato | Descrizione | Per chi |
|---------|-------------|---------|
| `json` (default) | Payload completo, indentato, `ensure_ascii=False`. | Parsing, agenti, `jq`. |
| `table` | Tabella rich con colonne ad alto segnale (per search: id, title, updated, author, bbox). | Umani a terminale. |
| `csv` | Stesse colonne della table, per fogli di calcolo. Vuoto se 0 righe. | Analisi dati. |
| `compact` | NDJSON: una riga JSON per record con `id`, `title`, `org`, `type`, `category`, `updated`, `resources`. **Solo per search.** | Agenti: scremare molti risultati a basso costo di token prima del [get](/cli/get.md). |

# Regole

- `get` con `csv`/`compact` è rifiutato (il dettaglio non è tabellare) — vedi [gestione errori](/conventions/error-handling.md).
- `--xml`/`--html` di `get` bypassano il dispatcher: testo grezzo su stdout.
- Il campo `resources` di `compact` elenca i tipi di risorsa fruibile (WMS, WFS, download, …) dedotti dai `links` del record, escludendo le rappresentazioni del metadato stesso (rel `alternate`/`icon`/`self`).
- `org` in `compact` viene da `apiso_OrganizationName_txt` (più informativo di `author.name`, che è il fallback).
