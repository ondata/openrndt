# openrndt — note di sviluppo

CLI Python per il Repertorio Nazionale dei Dati Territoriali (RNDT), modellata su
`~/git/idee/opensdmx` ma più snella (read-only, niente cache locale, niente multi-portal).

## Stack
- Python ≥ 3.12, gestione con `uv`.
- `httpx` (HTTP), `typer` (CLI), `rich` (table), `tenacity` (retry), `pydantic` (modelli).
- Test: `pytest` + `responses`/`respx`.

## Convenzioni
- Output di default: JSON su stdout (per uso AI). Flag `--format` per `table` o `csv`.
- Nessuna chiamata di rete nei test: tutto mockato.
- Codelist (TopicCategoryCode ISO 19115, sort, formati) sono costanti Python in `codelists.py`.
- Base URL configurabile via env `OPENRNDT_BASE_URL` o flag `--base-url`. Default: `https://geodati.gov.it/RNDT`.

## Bug noti dell'API RNDT
- Il parametro `dataCategory` documentato sulla pagina ufficiale **non filtra**: ritorna sempre il catalogo intero. Il filtro vero è `q=keywords_s:VAL`. La CLI traduce `--data-category` in questa clausola Lucene. Dettagli in `ref/rest-api-rndt.md`.

## Comandi
- `openrndt search` — ricerca metadati.
- `openrndt get <id>` — singolo metadato (JSON, `--xml`, `--html`).
- `openrndt discover` — codelist offline.

## File chiave
- `src/openrndt/cli.py` — entrypoint Typer.
- `src/openrndt/client.py` — wrapper httpx + tenacity.
- `src/openrndt/codelists.py` — ISO 19115 TopicCategoryCode.
- `skills/rndt-explorer/SKILL.md` — guida per agenti AI.
- `ref/` — documentazione API scaricata.

## Riferimenti
- Pagina ufficiale: https://geodati.gov.it/geoportale/eng/strumenti-en/rest-api
- Spec API (sito di test Esri Geoportal Server): https://gpt.geocloud.com/geoportal3/api/gpt_api.json
- Architettura sorella: `~/git/idee/opensdmx`
