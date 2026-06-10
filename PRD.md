# openrndt — CLI Python per il Repertorio Nazionale dei Dati Territoriali

## Obiettivo

Fornire una CLI Python, e una skill Claude Code di accompagnamento, per accedere ai
metadati del [RNDT](https://geodati.gov.it/RNDT/) tramite le REST API ufficiali. La CLI
è progettata per essere **orchestrata da un'AI**: input via flag espliciti, output JSON
strutturato di default, comandi di discovery per le codelist, output umani opzionali via
Rich.

Modello architetturale: il progetto sorella [`opensdmx`](https://pypi.org/project/opensdmx/)
(in `~/git/idee/opensdmx/`).

## Riferimenti

- Pagina ufficiale REST API: <https://geodati.gov.it/geoportale/eng/strumenti-en/rest-api>
- Spec completa Esri Geoportal Server (sito di test, non produzione):
  <https://gpt.geocloud.com/geoportal3/api/gpt_api.json>
- Documentazione raccolta in [`ref/`](./ref).

## Scope MVP (v0.1) — solo lettura

1. **`openrndt search`** — ricerca metadati con `q` (Lucene/Elasticsearch), `bbox`,
   `dataCategory` (ISO 19115), `time`, `sort`, `start`, `num`, `id`.
2. **`openrndt get <id>`** — dettaglio metadato in JSON (Elasticsearch `_source`),
   `--xml` per ISO 19139 grezzo, `--html` per HTML.
3. **`openrndt discover`** — codelist e parametri validi, **senza chiamate di rete**.

## Fuori scope (rimandato)

- OAuth login, publish/update/delete, setAccess/setApprovalStatus.
- Endpoint CSW e OGC API Records (non documentati sul RNDT pubblico).
- Cache locale persistente.
- Multi-portal config esteso (basta override `--base-url` / env `OPENRNDT_BASE_URL`).

## Vincoli tecnici

- Python ≥ 3.12, gestione con `uv`.
- Dipendenze runtime: `httpx`, `typer`, `rich`, `tenacity`, `pydantic`.
- Test: `pytest` + `respx` (HTTP mock, nessuna rete in CI).
- Default base URL: `https://geodati.gov.it/RNDT`. Override via env
  `OPENRNDT_BASE_URL` o flag `--base-url`.
- Output: `--format json` (default), `--format table`, `--format csv`.

## Criteri di accettazione

- `openrndt --format json search --q "catasto" --num 5` ritorna ≥ 1 risultato reale.
- `openrndt get <id> --xml` produce XML ISO 19139 valido.
- `openrndt discover` non fa chiamate di rete.
- `pytest` verde con HTTP mockato.
- La skill `rndt-explorer` guida un agente in 4 fasi: Discovery → Search → Detail → Download.

## Struttura del progetto

```
openrndt/
├── src/openrndt/             # codice CLI/libreria
├── skills/rndt-explorer/      # skill Claude Code (SKILL.md + references/)
├── ref/                        # doc API scaricata
├── tests/                      # pytest + fixture reali
├── pyproject.toml
├── README.md
├── CLAUDE.md
└── LOG.md
```
