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
- `org` è l'ente responsabile, `EnteResponsabile_s`, lo stesso campo su cui filtra `--org`; se manca, `apiso_OrganizationName_txt`, e in `compact` e `footprints` infine `author.name` (`record_org` in libreria). Fino alla 3.6.0 veniva prima `apiso_OrganizationName_txt`, che per molte schede della Regione Piemonte è il contatto «CSI Piemonte» (#23).
- `open` viene da `isOpendata`: è vero quando il campo è presente e non vuoto, la definizione di dato aperto di RNDT. Il campo è presente sul 72% dei record (55% escludendo l'Agenzia delle Entrate, che da sola ne vale 1177 su 3000) e in un terzo dei casi contiene il solo marcatore, quindi `open=false` non significa «dato chiuso» ma «l'ente non l'ha dichiarato lì».
- `license` sono i valori di `isOpendata` diversi dai marcatori `opendata`/`open data`; se non ce ne sono (dalla versione successiva alla 3.12.0), i valori di `apiso_OtherConstraints_s` e `apiso_AccessConstraints_s` che nominano una licenza: URL Creative Commons, URI delle licenze EU (`publications.europa.eu/resource/authority/licence/…`), «Creative Commons», sigle CC BY/CC0/CCBY, IODL, ODbL, opendatacommons. Le frasi sull'accesso («Nessuna limitazione al pubblico accesso», «Dato pubblico») restano fuori. Valori uniti da `; ` e riportati **come sono**: il RNDT non li normalizza, convivono `CC BY 4.0`, `CCBY`, URL e interi paragrafi di disclaimer. Misurato il 2026-11-02: delle 6.944 schede con `apiso_OtherConstraints_s` e senza `isOpendata`, 3.105 ottengono così una licenza. Il ripiego non tocca `open` (decisione di [#28](https://github.com/ondata/openrndt/issues/28)): ortofoto AGEA e DUSAF hanno `open=false` e `license` CC BY 4.0. Una licenza non aperta (es. by-nc-nd) entra in `license` come le altre: il campo è la licenza dichiarata, non un giudizio.
- `url` è il permalink della scheda sul portale, cioè il link `rel="alternate"` di tipo `text/html`: serve a citare la fonte senza ricostruire l'URL.
- Nella sola resa `table` le tre colonne cambiano forma: `url` non viene stampata (un permalink lungo rende illeggibile la tabella), `open` diventa `sì`/`no` e `license` viene troncata a 60 caratteri. In `csv`, `compact` e `footprints` i valori restano interi.
