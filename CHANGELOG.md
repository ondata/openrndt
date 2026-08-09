# Changelog

Tutte le modifiche rilevanti di questo progetto sono documentate qui.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.0.0/); il progetto segue [Semantic Versioning](https://semver.org/lang/it/).

## [Unreleased]

### Added

- `search` e `footprints` con 0 risultati stampano su stderr **suggerimenti contestuali** (allargare `--q` con wildcard, rimuovere `--data-category`/`--time`/`--bbox`, nominativo ente esatto e case-sensitive, ricerca per territorio) invece del solo «Nessun risultato».
- Se l'API risponde con errore HTTP mentre è attivo `--sort`, il messaggio su stderr ricorda i campi ordinabili su RNDT (`title`, `apiso_Modified_dt`, forma `campo:asc|desc`) e rimanda a `discover --what sort_values`.
- `resources` accetta **più ID in batch** (`resources <id1> <id2> …`): health-check di un gruppo di metadati in un comando; gli errori per-record (`ItemNotFoundError`, HTTP, rete) producono una voce con `error` senza fermare gli altri. Con un solo ID il formato dell'output resta invariato.
- `resources --check` **segue i redirect** (max 3) ma solo verso **host pubblici**, con la stessa validazione dell'URL iniziale: l'endpoint ARPA Veneto catalogato in `http` (301→`https`) ora risulta `ok=true, redirected=true` invece del falso negativo `ok=false`; un redirect verso un host non pubblico non viene seguito ed espone `error=redirect-blocked:…`.
- `resources --check` riporta per ogni endpoint **`latency_ms`** (durata complessiva della probe, distingue un servizio 200 veloce da uno lento) e i campi `redirected` / `redirect_count` / `redirect_url` (prima destinazione).

## [2.0.0] - 2026-08-09

### Changed

- `search --profile` senza `--format` esplicito ora produce direttamente una tabella, invece di stampare JSON ignorando in silenzio il preset di colonne. **Cambio di comportamento**: chi usava `search --profile gis` in uno script aspettandosi JSON deve aggiungere `--format json`.
- `search --profile` combinato con `--format json` o `--format compact` espliciti avvisa su stderr che il preset non si applica; l'output e il codice di uscita restano invariati.

## [1.1.0] - 2026-08-09

### Added

- Comando `resources`: estrae gli endpoint WMS/WFS/download di un metadato e ne verifica la raggiungibilità con un probe leggero (`HEAD`, fallback `GET` in streaming, senza mai scaricare il body). Blocca gli URL che non puntano a indirizzi pubblici e non segue i redirect.
- Comando `footprints`: esporta le bounding box dei risultati come GeoJSON FeatureCollection, pronto per QGIS.
- `search --profile gis` e `search --profile qgis`: preset di colonne per analisi rapida e per flussi QGIS/script (`wms_url`, `wfs_url`, `download_url`, `xmin..ymax`).
- Filtri temporali in `search`: `--updated-from`/`--updated-to` (su `apiso_Modified_dt`) e `--published-from`/`--published-to` (su `apiso_PublicationDate_dt`).
- `search --bbox-crs` accetta gli alias `EPSG:4326`, `CRS:84` e `WGS84`.
- Flag globale `--version` / `-V`, prima assente.
- Riferimento sul catalogo via CSW nella skill `rndt-explorer`, per flussi GDAL/OGR e QGIS.

### Fixed

- La versione del pacchetto ora ha una fonte unica (`pyproject.toml`, letta via `importlib.metadata`). Prima viveva in tre punti allineati a mano e uno era rimasto indietro: la CLI si annunciava a RNDT come `openrndt/0.1` pur essendo alla 1.0.0.
- Le date passate ai filtri sono validate anche sul calendario: `2024-13-40` viene rifiutata invece di finire nella query.
- La query utente `-q` viene racchiusa tra parentesi quando è combinata con altri filtri, così un `OR` non cambia significato per la precedenza di `AND`.

### Changed

- Documentazione allineata alle verifiche live sull'API: solo `title` e `apiso_Modified_dt` sono ordinabili; `apiso_PublicationDate_dt` esiste ed è filtrabile ma non ordinabile.

## [1.0.0] - 2026-07-17

### Added

- Type-checking `mypy --strict` in CI e come dipendenza dev.
- `py.typed` (PEP 561): la libreria distribuisce i tipi a chi la importa.
- CI GitHub Actions (`.github/workflows/ci.yml`): ruff, mypy, pytest su push/PR, matrice Python 3.12/3.13.
- Opzione globale `--timeout` per il timeout HTTP per singolo tentativo (default 30s).
- Metadata PyPI: `Repository`/`Issues` in `[project.urls]`.
- Sezione README per l'installazione da PyPI (`uv tool install openrndt` / `uvx`).
- Suite di test estesa a 55 test, coverage 99%.

### Fixed

- `--format <valore-invalido>` produceva un traceback completo invece di un messaggio leggibile: ora catturato ed esce con codice 2, coerente col principio "mai uno stack trace".

## [0.1.0] - 2026-05-27

### Added

- Comandi `search`, `get`, `discover` (MVP read-only sul RNDT).
- Libreria Python parallela alla CLI (`search`, `get_item`, `get_item_xml`, `get_item_html`, `ItemNotFoundError`).
- Formati di output `json` (default), `table`, `csv`, `compact` (NDJSON per agenti AI).
- Gestione errori pensata per orchestrazione LLM: mai stack trace, exit code distinti (0/1/2), messaggi self-contained su stderr.
- Retry esponenziale su timeout/5xx (`tenacity`).
- Codelist offline (ISO 19115, campi Lucene, formati) per `discover`, senza chiamate di rete.
- Skill Claude Code `rndt-explorer` per l'esplorazione guidata del catalogo.
- Bug noti dell'API RNDT documentati e compensati (`dataCategory` che non filtra, `sort` "amichevole" ignorato, item inesistente → 200 con `found: false`).
