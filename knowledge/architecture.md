---
type: Architecture
title: Architettura di openrndt
description: Moduli del package, flusso di una richiesta, punti di estensione.
tags: [architettura, moduli]
timestamp: 2026-07-17T00:00:00Z
---

Il package `src/openrndt/` è composto da 7 moduli piccoli e a responsabilità singola (~720 righe totali).

# Moduli

| Modulo | Responsabilità |
|--------|----------------|
| `cli.py` | Entrypoint Typer: comandi `search`, `get`, `discover`; traduzione eccezioni → messaggi ed exit code. |
| `search.py` | Chiamata e parsing di `/rest/metadata/search`; validazione parametri; `compact_results()` per l'output NDJSON. |
| `item.py` | Dettaglio singolo metadato (`/rest/metadata/item/{id}`) in JSON, XML ISO 19139, HTML; `ItemNotFoundError`. |
| `client.py` | `rndt_request()`: GET httpx con retry esponenziale tenacity (3 tentativi su timeout e 5xx), timeout default 30 s, User-Agent dedicato. |
| `codelists.py` | Costanti offline: categorie ISO 19115, valori `sort`, formati output, parametri di ricerca, campi Lucene. |
| `config.py` | Base URL (default `https://geodati.gov.it/RNDT`, override via env `OPENRNDT_BASE_URL` o flag `--base-url`) e timeout HTTP (default 30s, override via flag `--timeout`), letti da `client.rndt_request()`. |
| `output.py` | Dispatcher output: `json` (default), `table` (rich), `csv`, `compact` (NDJSON). |

# Flusso di una ricerca

1. `cli.py` riceve le opzioni e chiama `search.search()`.
2. `search.py` valida i parametri (`num` ≤ 5000, `start` ≥ 1), costruisce la query — traducendo `--data-category` nella clausola Lucene `keywords_s:VAL` perché il parametro ufficiale `dataCategory` [non filtra](/api/known-issues.md) — e chiama `client.rndt_request()`.
3. `client.py` esegue il GET con retry; `search.py` fa `raise_for_status()` e parsa il JSON.
4. `cli.py` passa il payload a `output.emit()` secondo il [formato scelto](/conventions/output-formats.md).

# Limiti architetturali noti

- `config._override`, `config._timeout` e `output._output_mode` sono stato globale a livello di modulo: corretto per la CLI (processo singolo), race condition latente se la libreria venisse usata in contesto multi-thread con base URL, timeout o formati diversi.
- Nessun client HTTP condiviso: ogni chiamata apre una nuova connessione (niente pooling). Trascurabile per la CLI.
