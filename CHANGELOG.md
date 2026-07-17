# Changelog

Tutte le modifiche rilevanti di questo progetto sono documentate qui.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.0.0/); il progetto segue [Semantic Versioning](https://semver.org/lang/it/).

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
