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
| `table` | Tabella rich con colonne ad alto segnale (per search: id, title, updated, org, author, open, license, bbox). | Umani a terminale. |
| `csv` | Stesse colonne della table, per fogli di calcolo. Vuoto se 0 righe. | Analisi dati. |
| `compact` | NDJSON: una riga JSON per record con `id`, `title`, `org`, `type`, `category`, `updated`, `indexed`, `open`, `license`, `url`, `resources`. **Solo per search.** | Agenti: scremare molti risultati a basso costo di token prima del [get](/cli/get.md). |

# Regole

- Il default `json` cede a un preset: `search --profile gis|qgis|default` **senza** `--format` esplicito passa da solo a `table`, perché i preset di colonne hanno senso solo per output tabellari. Con `--format json` o `compact` espliciti il preset non si applica e la CLI avvisa su stderr (output e exit code invariati). Meccanismo: `output.set_mode(mode, explicit=...)` marca il default come non-esplicito, così una scelta dell'utente non viene mai sovrascritta.
- `get` con `csv`/`compact` è rifiutato (il dettaglio non è tabellare) — vedi [gestione errori](/conventions/error-handling.md).
- `--xml`/`--html` di `get` bypassano il dispatcher: testo grezzo su stdout.
- Il campo `resources` di `compact` elenca i tipi di risorsa fruibile (WMS, WFS, download, …) dedotti dai `links` del record, escludendo le rappresentazioni del metadato stesso (rel `alternate`/`icon`/`self`).
- `org` in `compact` viene da `apiso_OrganizationName_txt` (più informativo di `author.name`, che è il fallback).
- `open` e `license` vengono da `isOpendata`: `open` è vero quando il campo è presente e non vuoto, `license` sono i suoi valori diversi dai marcatori `opendata`/`open data`, uniti da `; ` e riportati **come sono**. Il RNDT non li normalizza: nello stesso campo convivono `CC BY 4.0`, `CCBY`, URL e interi paragrafi di disclaimer. Il campo è presente sul 72% dei record (55% escludendo l'Agenzia delle Entrate, che da sola ne vale 1177 su 3000) e in un terzo dei casi contiene il solo marcatore, quindi `open=false` non significa «dato chiuso» ma «l'ente non l'ha dichiarato lì»: alcune schede aperte mettono la licenza solo in `apiso_OtherConstraints_s`.
- `url` è il permalink della scheda sul portale, cioè il link `rel="alternate"` di tipo `text/html`: serve a citare la fonte senza ricostruire l'URL.
- Nella sola resa `table` le tre colonne cambiano forma: `url` non viene stampata (un permalink lungo rende illeggibile la tabella), `open` diventa `sì`/`no` e `license` viene troncata a 60 caratteri. In `csv`, `compact` e `footprints` i valori restano interi.
