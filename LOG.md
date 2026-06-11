# LOG

## 2026-06-11

- **Nuovo formato `--format compact` (NDJSON per agenti).** Quarto formato di output per `search`: una riga JSON per record con i soli campi ad alto segnale (`id`, `title`, `org`, `type`, `category`, `updated`, `resources`). Pensato per far scremare molti risultati a basso consumo di token prima del `get`. Spunto dal progetto Copernicus-Services-Products-Metadata (rendering sintetico dei risultati; lì *prima* della ricerca perché catalogo locale, qui *dopo* perché catalogo remoto).
  - Libreria: `compact_results(payload)` in `search.py` — `org` da `apiso_OrganizationName_txt` (fallback `author.name`), `category` da `apiso_TopicCategory_s` (fallback keyword ISO), `resources` = dctype dei `links` (escluse rappresentazioni del metadato), dedup+sort.
  - `output.py`: aggiunto mode `compact` + branch NDJSON. `get --format compact` rifiutato come csv (dettaglio non tabellare).
  - Test: +6 (4 libreria, 2 CLI). 37/37 verdi, ruff pulito.
  - Doc: README (formati + Per agenti AI), SKILL.md, `docs/future-ideas.md` con gli altri spunti Copernicus (rerank semantico, snapshot/cronologia CI, Parquet).
- **Verifica `--bbox`** (challenge utente): il filtro funziona (semantica overlaps; 485→21 record in Sicilia, 0 in oceano). Il rumore "Toscana sotto bbox Sicilia" è dovuto a record con bbox dichiarato errato (tutta Italia `6.6,35.5,18.5,47.1`) — problema di qualità nei metadati sorgente, non del filtro.
- **Fix review PR #7** (Copilot + Greptile): SKILL elenca anche `updated` tra i campi compact; help `--format` chiarisce che `compact` è solo per `search`; docstring `emit()` csv allineata (output vuoto, non errore); `_topic_category` ora cerca la categoria ISO sia in `keywords_s` sia in `categories` (prima saltava il fallback se `keywords_s` era popolato ma senza valori ISO) +1 test; `docs/future-ideas.md` marca il compact come implementato. 38/38 verdi.
- **Nuova reference skill `references/ogc-services.md`**: guida all'esplorazione dei servizi OGC (WMS/WFS/WCS/WMTS) linkati nel catalogo RNDT con GDAL/OGR a output JSON. Punti verificati: `gdalinfo`/`ogrinfo -json` danno solo Nome+Titolo (no `queryable`/abstract → solo nel GetCapabilities, che ha tutto), `gdallocationinfo` per GetFeatureInfo, `ogr2ogr` per download vettoriale. Esempio catasto AdE (layer `fabbricati`, non `BU.Building`; WFS senza fabbricati; 3 layer queryable). Linkata da Fase 4 della SKILL.

## 2026-06-10 (continua)

- **README: sezione "Esempi di conversazione con un'AI"** per utenti GIS desktop (non CLI). 7 scenari conversation-first (domanda in linguaggio naturale → comando openrndt leggibile → URL WMS/WFS da incollare in QGIS), tutti con risultati RNDT reali e verificati live: uso suolo Emilia-Romagna (WMS getCapabilities testato 200), catasto Piemonte, ortofoto (Sardegna/Lodi/Piemonte), reticolo idrografico WFS (ISPRA/ARPA Veneto/Basilicata), 430 dataset Regione Lombardia, bbox area Bologna (40, framing onesto "sovrapposizione"), 259 frane open data. Niente jq mostrato, niente link con IP interni (bug issue #2).
- **Fix review PR #6** (Greptile + Copilot). Risolto il tema centrale: `json.JSONDecodeError` (sottoclasse di `ValueError`) su risposte 2xx con body non-JSON.
  - `get`: ora cattura `json.JSONDecodeError` → messaggio leggibile + exit 1 (prima → traceback, violava "mai stack trace").
  - `search`: separato `JSONDecodeError` (exit 1, "risposta inattesa") da `ValueError` di validazione parametri (exit 2), che prima collassavano sullo stesso exit 2 fuorviante.
  - `_http_error()`: fallback a `config.get_base_url()` quando `exc.request` manca (es. `ConnectError` senza request) → messaggio sempre self-contained; tipato `-> NoReturn`.
  - Doc: README chiarisce che i retry valgono per timeout/5xx, non per `ConnectError`; docstring `search()`/`get_item()` documentano `json.JSONDecodeError`. Rimossa fixture inutile in un test. 31/31 verdi (+2: malformed-json su search e get).

- **Allineamento ai principi "CLI per orchestrazione LLM" di opensdmx.** Fix di principio (errori leggibili, niente stack trace) + doc:
  - `cli.py`: errori di rete (`ConnectError`, `TimeoutException` dopo retry) e HTTP ora catturati via `httpx.HTTPError` → messaggio leggibile su stderr + exit 1, **niente più traceback** (era il gap principale: porta morta/no-network dumpava lo stack). Helper `_http_error()` condiviso da `search`/`get`.
  - `get --format csv` (dettaglio non tabellare) → messaggio esplicito + exit 1, **senza chiamata di rete**, invece di output vuoto silenzioso. `search` 0-risultati (csv/table) → avviso su stderr, exit 0. Rimosso anche l'exit 1 muto su payload non-dict.
  - Libreria: docstring di `search()`/`get_item()` documentano le eccezioni propagate (`httpx.HTTPError`); README sezione libreria + nuova sezione "Per agenti AI" con i principi di design.
  - `cli.py`: parametri fuori range (`--num` > 5000, `--start` < 1) ora catturano `ValueError` → messaggio leggibile + exit 2 (parametri non validi), niente traceback.
  - Decisione: **no** rename `--format`→`--output` (parità solo ortografica, contraddice CLAUDE.md) e **no** comando `which` (scope creep). 29/29 test verdi (+5: connect-error/no-traceback, csv-zero-results, get-csv-non-tabellare, invalid-num/no-traceback).

- PR #3 mergiata su main (`docs/sort-csw-limitations`). Issue aperte: #4 (data pubblicazione non ordinabile via REST), #5 (CSW `SortBy` ignorato, non conforme INSPIRE Discovery Services v3.1). Installazione CLI globale aggiornata.
- **Scoperta sort** (verificata live, cross-validata su endpoint test Esri): il sort reale è `campo:asc|desc` su campi sortable (`_s`/`_dt`/`_i`); `dateDescending`/`dateAscending` documentati NON ordinano (ignorati). Campi `text` (`title` nudo) → errore ES "Fielddata is disabled". Nessun campo data-pubblicazione indicizzato: proxy = `apiso_Modified_dt:desc`.
- **Scoperta CSW**: `/csw` ignora del tutto `<ogc:SortBy>` (qualsiasi proprietà/direzione) → non conforme INSPIRE Technical Guidance Discovery Services v3.1.
- Allineati: `codelists.py` (SORT_VALUES + note campi data), `cli.py` (help `--sort`), `search.py` (docstring), `ref/rest-api-rndt.md` (note sort + CSW), skill `SKILL.md` + `search-syntax.md` (sezione Ordinamento + filtro ente robusto). 25/25 test verdi.
- Nota qualità dati: stesso ente con molte varianti di `apiso_OrganizationName_txt` → filtrare per `EnteResponsabile_s` o prefisso id (codice IPA ente capofila).
- Skill `rndt-explorer` aggiornata con nuovi campi Lucene scoperti live: `apiso_OrganizationName_txt`, `EnteResponsabile_s`, `apiso_Type_s`, `PuntoDiContattoEmail_s`, `PuntoDiContatto_s`, `PuntoDiContattoSitoWeb_s`.
- Documentata distinzione `author.name` (username sistema) vs `apiso_OrganizationName_txt` (nome ente).
- Documentato codice IPA ricavabile dal prefisso dell'`id` (es. `r_sicili:uuid` → IPA `r_sicili`).
- Aggiunti esempi query live per filtro per organizzazione, ordinamento per data, filtro per tipo risorsa.
- PR #1 mergiata su main (`fix/item-not-found-and-internal-links`).
- Issue #2 aperta: segnalazione bug RNDT (link IP interno + 500/501 per ID inesistente).

## 2026-06-10

- Valutazione qualità (v0.1.0): punteggi per dimensione in `docs/evaluation.md`.
- Fix stale assertion in `tests/test_discover.py`: aggiunto `lucene_fields` al set atteso.
- Rimossa dipendenza `pydantic` da `pyproject.toml` (non usata).
- Rimossa variabile morta `last_exc` in `client.py` (ruff F841).
- Gestione `httpx.HTTPStatusError` in `cli.py` (search + get): messaggio leggibile su stderr invece di traceback.
- Sostituito `assert isinstance(payload, dict)` con check esplicito in `cli.py`.
- Nuovi test retry in `tests/test_retry.py`: 503→200 (retry ok) e 3×503 (propaga errore). Totale: 21/21 test verdi.

## 2026-05-27

- Bootstrap progetto: `pyproject.toml`, `LICENSE` MIT, `.python-version` 3.12, `.gitignore`, `CLAUDE.md`, `LOG.md`.
- PRD ripensato e formalizzato (v0.1 read-only: `search`, `get`, `discover`).
- Endpoint produzione confermato live: `https://geodati.gov.it/RNDT/rest/metadata/search` → HTTP 200, 23.580 record nel catalogo.
- Endpoint `item/{id}` JSON/XML/HTML verificati live (HTTP 200).
- Cartella `ref/` con spec `gpt_api.json` (sito di test Esri Geoportal Server) e doc estratta dalla pagina ufficiale.
- CLI implementata: `src/openrndt/{config,client,codelists,search,item,output,cli}.py` + entry point Typer `openrndt`. Installata in editable nel venv `~/.venvs/data`.
- 19 test pytest verdi (HTTP mockato con `respx`, fixture reali in `tests/fixtures/`).
- Skill `rndt-explorer` con SKILL.md (137 righe, 4 fasi) + 5 references verticali (categories, search-syntax, result-structure, output-formats, workflows).
- **Bug RNDT scoperti durante validazione** (documentati in `tmp/bugs-incoerenze.md`):
  1. Parametro `dataCategory` documentato non filtra — fix: traduzione automatica `--data-category` → `q=keywords_s:VAL` lato CLI.
  2. Combinazione `time` + `q` su campo specifico → 0 risultati.
  3. Campo `updated` riflette reindex catalogo, non data dataset.
  4. `total` di tipo variabile (int o `{value, relation}`).
  5. Confusione `geodati.gov.it` vs `gpt.geocloud.com`.
- Piano completo in `/home/aborruso/.claude/plans/studia-questo-prd-md-mettilo-partitioned-papert.md`.
- Installazione globale via `uv tool install /home/aborruso/git/idee/openrndt/` → binario in `~/.local/bin/openrndt` (venv isolato). Aggiornamento: `uv tool install --reinstall <path>`. Disinstallazione: `uv tool uninstall openrndt`.
