# LOG

## 2026-08-09 (v3.0.0: date separate, ricerca per ente, fix latency)

- **`updated` e `indexed` non sono più lo stesso campo**. In `table`/`csv`/`compact`/`footprints`, `updated` è ora `apiso_Modified_dt` (data della scheda, quella su cui filtrano `--updated-from/--updated-to`) e `indexed` è `sys_modified_dt` (indicizzazione nel catalogo, il campo top-level `updated` dell'API). Era una collisione di nome interna alla CLI: si filtrava su un campo e se ne leggeva un altro, e dopo `--sort apiso_Modified_dt:desc` la colonna mostrata era scorrelata dall'ordine. Verificato live: record catasto con `updated 2026-04-25T15:37:34Z` e `apiso_Modified_dt 2019-11-13`. Rottura del formato → **3.0.0**.
- Dove non si può rinominare (`--format json`, passthrough del payload API) la CLI stampa una nota su stderr, ma solo quando la ricerca usa un filtro o un ordinamento sulle date; la tabella porta la legenda in calce.
- **`--org` / `--org-exact` su `search` e `footprints`**. `--org` cerca la frase su `apiso_OrganizationName_txt` (campo analizzato: case-insensitive, ordine dei token irrilevante). Verificato live: `--org "comune di torino"` → 269 record, tutti e soli del Comune di Torino. `--org-exact` resta per il confronto esatto su `EnteResponsabile_s`.
- **Su zero risultati con `--org` la CLI mostra i nomi reali in catalogo**: una sola query esplorativa sul token più distintivo, aggregata a valle (l'API ignora `facet`, verificato). `--org "comune di bologna"` → `Citta' metropolitana di Bologna | Regione Emilia-Romagna`: il Comune di Bologna non pubblica in proprio.
- **Fix `latency_ms` sempre 0** in `resources --check`: la durata era misurata in secondi ed emessa come millisecondi. ISPRA WMS/WFS/download passano da `0/0/0` a `147/139/129` ms. Il test esistente passava anche col bug (`isinstance(int)` e `>= 0`): ora la durata è iniettata e il valore atteso è esatto.
- **Corretto un suggerimento sbagliato introdotto ieri**: su zero risultati la CLI consigliava per gli enti `contact_organizations_s:*nome*` definendolo «esatto e case-sensitive». Live: `*bologna*` → 0, `*Bologna*` → 112 ma quasi tutti di Regione E-R e ARPAE che *nominano* Bologna. Ora rimanda a `--org`.
- Tabella profilo `default`: aggiunta la colonna `org`. `author` contiene la sorgente di harvest (`csw.piemonte`), non l'ente.
- Verificata e smentita la debolezza «colonne troncate» del report: Rich usa `overflow="fold"`, manda a capo senza perdere caratteri.
- API di libreria: `record_dates()` e `organization_names()` esportate al top-level insieme a `compact_results()`.
- Test 123/123 verdi, ruff e mypy puliti. README, skill (`SKILL.md`, `search-syntax.md`, `result-structure.md`, `output-formats.md`, `workflows.md`) e bundle `knowledge/` allineati.

## 2026-08-09 (CLI: resources con redirect, latenza e batch)

- **`resources` segue i redirect (max 3) solo verso host pubblici**: validazione per hop con la stessa allowlist dell'URL iniziale. L'endpoint ARPA Veneto (`http://gaia.arpa.veneto.it/…`, 301→https) prima dava `ok=false` — un falso negativo su un servizio funzionante — ora `ok=true, redirected=true`. Un 3xx verso host non pubblico (es. link-local) non viene seguito: `error=redirect-blocked:…`. Mantenuta e rafforzata la postura fail-closed (niente follow cieco).
- **`latency_ms` per endpoint**: durata complessiva della probe; distingue un 200 veloce da uno lento. Verificato live: WMS/WFS ARPA Veneto 1ms dopo il redirect.
- **Batch**: `resources <id1> <id2> …` → `{"count": N, "results": [per-id]}`; errori per-record raccolti (metadato inesistente, HTTP, rete) senza fermare il batch. Formato a ID singolo invariato (retro-compatibile). Verificato live su 2 metadati (ARPA Veneto + ISPRA).
- Campi riga: `redirected`, `redirect_count`, `redirect_url` (prima destinazione) aggiunti all'output del check.
- Test: +6 (redirect bloccato vs seguito, too-many-redirects, latency, batch 2 id, batch con errore) e aggiornato il test «non segue redirect» → «blocca redirect verso host non pubblico». 106/106 verdi, ruff e mypy puliti.
- Skill aggiornata (Fase 4: batch, redirect, latency, campi del check) e `references/result-structure.md` con la tabella dei campi del check.

## 2026-08-09 (CLI: zero risultati e sort parlanti)

- **`search`/`footprints` con 0 risultati ora spiegano perché**: su stderr arrivano suggerimenti contestuali — wildcard su `--q` (solo per testo libero; per `campo:valore` ricorda che il valore è esatto e i campi `_s` sono case-sensitive), rimozione di `--data-category`/`--time`/`--bbox` uno alla volta, e per gli enti il nominativo esatto in `contact_organizations_s` oppure la ricerca per territorio (`--bbox` + `AmbitoTerritoriale_s:Locale`). Incentrato sul caso reale verificato: `apiso_OrganizationName_txt:"Comune di Bologna"` → 0.
- **Errore HTTP con `--sort` attivo → promemoria dei campi ordinabili** (`title`, `apiso_Modified_dt`; `dateAscending`/`dateDescending`/`relevance` ignorati; rimando a `discover --what sort_values`). Verificato live: `--sort title` (senza direzione) → 500 con contesto leggibile.
- Test: +2 (hint su stderr in json con `total` a oggetto, sort-500 con campi ordinabili), estesi i due zero-results esistenti (csv, compact) con l'assert sui suggerimenti. 101/101 verdi.
- Skill `rndt-explorer` aggiornata: sezione «Zero risultati? Leggi i suggerimenti» in Fase 2 (cause ricorrenti: periodo vuoto, ente non indicizzato, bbox nazionale), nota sort-500, e sezione dedicata in `references/search-syntax.md`.

## 2026-08-09 (rework esempi README)

- **README riscritto con esempi verificati live** (sezione "Esempi verificati", 11 scenari): ogni comando eseguito contro il catalogo reale il 2026-08-09, URL controllati con HTTP, output citati verbatim. Stato aggiornato a v2.0.
- **Audit degli esempi precedenti**: 2 URL su 8 morti — WMS ortofoto Provincia di Lodi (`sdi.provincia.lodi.it`, DNS ok ma TCP down a 2 tentativi) e WFS Regione Basilicata (`rsdi.regione.basilicata.it`, idem) → sostituiti con endpoint verificati 200 (Lombardia Ortofoto 2024, Sardegna, Piemonte mapproxy; WFS ARPA Veneto + ISPRA).
- **Numeri magici invecchiati**: Lombardia 430→438, edificato Bologna 40→44, frane open data 259→268 (catalogo cresce) → nel nuovo README i totali sono quelli del giorno di verifica, con nota esplicita.
- **Nuovi esempi wow verificati**: record → WFS → `ogr2ogr` GPKG in 2.2s (ARPA Veneto, 585 KB); sweep 108 WMS unici tema Idrografia in 10s; comune → 4 dataset CMBO con email contatto; footprint GeoJSON QGIS-ready.
- Nota onesta documentata: l'endpoint ARPA Veneto è catalogato in `http` e risponde con redirect a `https` (per questo `resources` senza `--no-check` dà 301, non 200 — `ogr2ogr` lo segue da solo).

## 2026-08-09 (valutazione utilità per figure professionali)

- **Valutazione v2.0.0 con verifica live contro l'API reale** in `docs/evaluation-v2.0.0.md`, scenari per tecnico GIS, analista spaziale e ufficio comunale. Esito: ottimo per GIS e analista, buono con attrito per il comune.
- Punto debole principale confermato dal vivo: **la ricerca per ente**. `apiso_OrganizationName_txt:"Comune di Bologna"` → 0 (testo analizzato), `EnteResponsabile_s` e prefisso IPA `c_a944` → 0 (comune non indicizzato con quei nomi), wildcard su `contact_organizations_s` → over-match. Percorso robusto per il comune: `AmbitoTerritoriale_s:Locale` + `--bbox` (15 record per l'area di Bologna vs 2789 con solo bbox).
- Verifiche live di conferma: filtro `--time` combinato (42 = atteso), `resources` con status 200 e probe HEAD, CSV `--profile qgis` pronto per QGIS, `footprints` GeoJSON valido, XML ISO 19139 valido, 5000 record `compact` in 36s, sort invalido → HTTP 500 con messaggio minimo (non traceback). 99/99 test verdi.
- Nuove proposte in `docs/future-ideas.md`: flag `--org`/`--suggest-org`, zero-risultati e sort invalido parlanti, `resources` in batch con latenza, tabella `--wide`.

## 2026-08-09 (release 2.0.0)

- **`--profile` era una trappola silenziosa**: `openrndt search --profile gis` stampava JSON, perché il preset di colonne vale solo per `table`/`csv` e `--format` è globale (va prima del sottocomando). Nessun errore, nessun avviso: l'opzione veniva semplicemente ignorata. Ora `--profile` senza `--format` esplicito attiva da solo `table`, e con `--format json|compact` espliciti la CLI dice su stderr che il preset non si applica.
- Il meccanismo è `output.set_mode(mode, explicit=...)`: il default `json` è marcato non-esplicito, così i comandi possono sovrascriverlo senza sovrascrivere una scelta dell'utente. Stessa distinzione su `--profile`, che passa a default `None` per separare «non passato» da `--profile default`.

## 2026-08-09 (release 1.1.0)

- **Rilasciata la 1.1.0**: comandi `resources` e `footprints`, profili `--profile gis|qgis`, filtri temporali `--updated-*`/`--published-*`, alias CRS per la bbox, flag `--version`. PR #12 e #13.
- **`resources` dichiarava rotti endpoint funzionanti**, sul suo stesso esempio di documentazione: il fallback a `GET` era limitato a `405/501`, ma i WMS/WFS reali rifiutano `HEAD` con 403/500 pur rispondendo 200 a `GET` (verificato su `age:D_E973_MARSAGLIA`, entrambe le risorse davano `ok=false`). Ora qualunque `4xx/5xx` viene riverificato in streaming senza scaricare il body. Difetto trovato da noi, non dai reviewer.
- **La versione aveva tre punti allineati a mano e uno era già disallineato**: pacchetto a 1.0.0, `USER_AGENT` fermo a `openrndt/0.1` dalla release precedente. Ora `_version.py` legge i metadati della distribuzione: `pyproject.toml` è l'unico punto da alzare, e `tests/test_version.py` impedisce il ritorno della deriva.
- **Hardening del check risorse** dopo sei giri di review automatica: allowlist di schema, blocco degli indirizzi non pubblicamente instradabili (incluso il CGNAT `100.64.0.0/10`, che sfuggiva a `is_private`/`is_reserved`), fail-closed quando il DNS non risolve, redirect non seguiti. **Declinato il pinning DNS**: chiude una finestra TOCTOU reale ma romperebbe il routing per nome sugli endpoint che lo strumento esiste per verificare — il reviewer ha ritirato il rilievo.
- **Un test faceva risoluzione DNS reale** (`test_cli_resources_json_with_check` verso `*.agenziaentrate.gov.it`), contro la regola «nessuna chiamata di rete nei test». Ora `conftest.py` stubba `getaddrinfo` per tutta la suite.
- Aggiunti in locale (non versionati, `.claude/` è gitignored): hook di lint+mypy sugli edit, hook che avvisa quando `src/` cambia senza `knowledge/` e `LOG.md`, skill `/release`, subagent `rndt-api-verifier`.

## 2026-07-27 (verifica post-email RNDT)

- **Riverificati live i 6 punti dell'email a info@rndt.gov.it (18/07): nessuno risolto.** (1) checkbox «Considera valori vuoti»: stesso JS inline (AND dei 3 range 1900–2100), ancora spuntata di default; (2) `sort=apiso_PublicationDate_dt:desc|asc` ancora ignorato (`apiso_Modified_dt` ok); (3) CSW: esempio §2.2.1 → 0 record e `numberOfRecordsMatched="[object Object]"`, GetDomain ancora `false`; (4) link `alternate` ancora su `192.168.3.34:8080` (anche OpenSearch nel GetCapabilities); (5) `dataCategory` ancora no-op (23.650 = totale); (6) nessun campo licenza normalizzato, conteggi CC invariati a meno dei nuovi record.
- Catalogo cresciuto da 23.632 a 23.650 record.

- **Ispezione del frontend ufficiale** (Ricerca Dettagliata) con `agent-browser` (cattura network/HAR headed). Riscritti `tmp/bugs-incoerenze.md` e `tmp/proposte-rndt.md` con le prove di oggi.
- **Correzione importante**: `apiso_PublicationDate_dt` **esiste** (8.402/23.632 record) ed è **filtrabile** via `q=…:[range]`, ma **non ordinabile**. Contraddice la nota precedente ("campo inesistente"): corretti `knowledge/api/known-issues.md` e issue #4. Il *filtro* per data di pubblicazione del metadato si può; l'*ordinamento* no.
- **Solo `title` e `apiso_Modified_dt` sono ordinabili** (confermato indipendentemente dal menu "ORDINA PER" del portale, che offre solo quei due). Ignorati `orderBy=`, `searchText=`, `after/before` (parametri nativi Esri che il frontend costruisce ma l'endpoint pubblico non onora).
- **Bug nuovo → issue #9**: la Ricerca Dettagliata mette in AND tutti e 3 i campi data quando ne filtri uno solo; "Considera valori vuoti" non funziona (campo assente non matcha `[1900 TO 2100]`). "incendi creati dal 2024 a oggi" → portale 0, reali 15.
- **Campo licenza incoerente**: `isOpendata` a volte `null` con la licenza solo in `apiso_OtherConstraints_s` (tutti i dataset AIB del MASE) → `isOpendata:*` perde open data reali. Aggiunto a issue #8.
- Riconfermati live #2 (IP interno 192.168.3.34, anche nei link export della UI ufficiale), #5 (CSW SortBy ignorato).
- Contatti supporto RNDT trovati: `info@rndt.gov.it`, Skype `rndt.help`.

## 2026-07-17 (skill audit)

- **Audit live della skill `rndt-explorer`** (comandi eseguiti contro l'API reale). Esito: struttura a 4 fasi solida, 4 punti stale corretti:
  - `workflows.md` #3/#4 usavano `--sort dateDescending` (che NON ordina, riconfermato live) → sostituito con `apiso_Modified_dt:desc` + warning.
  - `workflows.md` citava `apiso_PublicationDate_dt` → campo inesistente (verificato su record reale), rimosso; lista campi data corretta.
  - **Scoperta: il sort su `title` ora funziona** (`title:asc` ordina alfabeticamente) — l'API è cambiata rispetto a maggio-giugno, quando dava "Fielddata is disabled". Aggiornati `search-syntax.md`, `codelists.py` (commento), `knowledge/api/known-issues.md`. I campi garantiti sortable restano `_s`/`_dt`/`_i`.
  - `output-formats.md` non menzionava `compact` → aggiunta sezione dedicata (incl. `resources: []` → serve `get`).
  - SKILL.md: frontmatter v0.1→1.0, installazione da PyPI in compatibility, opzioni globali `--timeout`/`--base-url`.
  - **Nuovo workflow 7 per data journalist** (verificato end-to-end live su record ISPRA "Popolazione rischio alluvioni"): compact+isOpendata → `search --id` per link con dctype → `get` per licenza/ente/data (citazione fonte) → `ogr2ogr` dal WFS. Note oneste: enclosure raro, `isOpendata` a volte generico, download spesso dietro portali regionali.
  - Sanity numbers aggiornati al 2026-07-17 (catalogo 23.580→23.632).
  - Aggiunti `apiso_CRS`, `apiso_Format_s`, `isOpendata` ai campi utili di `search-syntax.md` (per operatori GIS).
- 55/55 test, ruff e mypy verdi (unica modifica codice: commento in `codelists.py`).

## 2026-07-17

- **Valutazione readiness produzione v0.1.0** in `docs/evaluation-v0.1.0.md`: codice production-grade, gap tutti infrastrutturali (no CI, no mypy, metadata PyPI incompleti, manca `py.typed` e CHANGELOG). Roadmap verso v1.0 inclusa.
- **Knowledge bundle OKF** in `knowledge/`: documentazione del progetto in Open Knowledge Format (markdown + frontmatter YAML, leggibile da umani e agenti). 18 file: project, architecture, skill, cli/ (search, get, discover), library/, api/ (endpoint + bug noti verificati live), conventions/ (errori, output, testing). Validato conforme OKF v0.1 (frontmatter `type`, cross-link integri).
- **`py.typed`** (PEP 561) aggiunto in `src/openrndt/`: verificato presente nel wheel dopo `uv build` senza bisogno di config aggiuntiva (`uv_build` lo include automaticamente). 38/38 test verdi. Primo punto della roadmap v1.0 in `docs/evaluation-v0.1.0.md`.
- **`mypy --strict` pulito** (secondo punto roadmap): aggiunto al gruppo dev, config `[tool.mypy]` in `pyproject.toml`. 5 fix reali: `discover()` in `cli.py` riusava la variabile `section` con due tipi diversi (rinominata `values`); `dict` senza type-arg in `client.py`; 3 `no-any-return` (`response.json()` non annotato) in `search.py`/`item.py`, risolti annotando la variabile o con `cast`. 38/38 test e ruff ancora verdi.
- **CI GitHub Actions** (terzo punto roadmap): `.github/workflows/ci.yml`, matrice Python 3.12/3.13, step `uv sync --locked` → `ruff check` → `mypy` → `pytest -v` su push/PR verso main. Sequenza verificata localmente prima del commit.
- **Metadata `[project.urls]`** (quarto punto): aggiunti `Repository`/`Issues` verso `github.com/ondata/openrndt`; rinominati i link RNDT (`RNDT Portal`/`RNDT REST API`) per chiarire che non sono il repo del codice.
- **README: installazione da PyPI** (quinto punto): sezione dedicata con `uv tool install openrndt`/`uvx`, nota onesta che il package non è ancora pubblicato; installazione locale riorganizzata in sezioni "Da locale" / "Per sviluppo".
- **`--timeout` configurabile in CLI** (sesto punto): nuova opzione globale, stesso pattern di `--base-url` (override in `config.py`: `get_timeout()`/`set_timeout()`, usato come default da `client.rndt_request()`). Verificato live: `--timeout 0.5` contro un IP non instradabile fallisce in ~1.5s con messaggio leggibile ed exit 1 (no traceback), invece dei ~90s del default. 38/38 test, ruff e mypy verdi.
- **v1.0.0 pubblicata** (ottavo punto, completo): `CHANGELOG.md`, bump versione, classifier PyPI `3 - Alpha` → `5 - Production/Stable`. Commit `08ecc36` pushato su `main`, tag annotato `v1.0.0` pushato. `uv build` + `twine check` PASSED, poi `uv publish` (token da `~/.pypirc`, dry-run prima del reale). **openrndt 1.0.0 è live su PyPI**: <https://pypi.org/project/openrndt/>. Verificato live: `uvx --from openrndt==1.0.0 openrndt --help` funziona da installazione pubblica pulita.
- **Coverage 89%→99%** (settimo punto) e **bug reale trovato nel farlo**: `--format <valore-invalido>` produceva un traceback completo (verificato live) — violava il principio cardine "mai uno stack trace". Fix: `ValueError` di `output.set_mode()` ora catturato nel callback `_root` di `cli.py` → messaggio leggibile + exit 2. +17 test: `tests/test_output.py` nuovo (rami table/csv irraggiungibili dalla CLI, testati chiamando `output.emit()` direttamente); percorsi di successo mai testati a livello CLI (`get` default json, `get --html`, `get --format table`, `discover` in table); `search --format compact` zero risultati; payload di risposta non-dict; parametro `--modified`; `keywords_s` come stringa singola; download senza `dctype`. Aggiunto `pytest-cov` (dev) e fixture di reset per `output_mode`/`timeout` in `conftest.py` (stesso pattern di `_reset_base_url`). Coverage residua (99%, righe 230/234 di `cli.py`): solo `main()`/`__main__` boilerplate. 55/55 test, ruff e mypy verdi.

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
