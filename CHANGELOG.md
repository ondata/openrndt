# Changelog

Tutte le modifiche rilevanti di questo progetto sono documentate qui.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.0.0/); il progetto segue [Semantic Versioning](https://semver.org/lang/it/).

## [3.3.0] - 2026-08-31

### Added

- **`get` con `--format json` (default) restituisce un documento normalizzato** invece della busta Elasticsearch grezza: stessi campi delle risposte di `search` (id, title, org, type, category, date updated/indexed) più `data_date` (data del dato), `contact` (nome/email/sito del punto di contatto designato, da `PuntoDiContatto*`), `bbox` (da `envelope_geo`), `lineage`, `resources` (come `resources --no-check`) e `url` (permalink citabile). `_source` e i flag della busta restano inalterati in coda.
- **`get --raw`**: ripristina la busta Elasticsearch completa, comportamento ante 3.3.0.
- **`search --format compact` arricchito di due campi**: `email` (punto di contatto designato, `PuntoDiContattoEmail_s`) e `download` (URL dichiarati da `url_download_s` + `url_http_download_s`, normalizzati in lista).
- **`resources` legge anche `resources_nst`**: le risorse con tipo assegnato dal catalogo (`url_s` + `url_type_s`) ora hanno precedenza su `link`/`links_s`/`webServices_s`, deduplicando per URL.

### Changed

- Il contratto documentato di `get` (reference della skill, `references/result-structure.md`) coincide ora con l'output reale, che prima non lo rispettava.

## [3.2.0] - 2026-08-30

### Fixed

- **`resources` non dichiara più morti i server con TLS legacy**: la probe usa un contesto TLS con `DEFAULT:@SECLEVEL=1`. Diversi GeoServer di enti pubblici (es. `sgi2.isprambiente.it`) negoziano solo TLS 1.2 con `AES128-SHA`, che OpenSSL a livello 2 rifiuta: httpx otteneva `Connection reset by peer` mentre curl rispondeva 200. Certificato e hostname restano verificati. Inoltre, se la `HEAD` fallisce per un errore di trasporto (non per timeout, che non viene ritentato), si riprova con una `GET` in streaming prima di segnare l'errore; `method` riporta l'ultimo tentativo.
- **`discover --what search_params` diceva il contrario del vero su due punti.** L'operatore implicito fra termini di `--q` è **OR**, non AND (`catasto siciliana` → 8.903 = `catasto OR siciliana`; `catasto AND siciliana` → 1): per restringere serve `AND` esplicito. E il leading wildcard funziona anche su campo esplicito (`EnteResponsabile_s:*Siciliana` → 62), mentre la codelist lo dava per non supportato. `discover --what sort_values` marcava `relevance` come «verificato»: è ignorato dal server come `dateDescending`.

### Note

- Il check di `resources` resta una prova di raggiungibilità del GetCapabilities: un WMS può rispondere 200 lì e fallire su ogni GetMap (visto sul PCN, `wms.pcn.minambiente.it`, che non raggiunge il proprio PostGIS). Per dichiarare un servizio usabile serve una GetMap reale (vedi la skill, `references/ogc-services.md`).

## [3.1.0] - 2026-08-29

### Added

- **`open`, `license` e `url` negli output sintetici**: `compact`, i tre profili di `table`/`csv` e le proprietà del GeoJSON di `footprints`. `open` è vero quando il record dichiara `isOpendata`, `license` sono i valori di quel campo diversi dai marcatori `opendata`/`open data`, riportati **come sono**: il RNDT non li normalizza e nello stesso campo convivono `CC BY 4.0`, `CCBY`, URL e paragrafi di disclaimer. Misurato su 3000 record: il campo è presente sul 72%, che scende al 55% escludendo l'Agenzia delle Entrate (1177 record da sola), e in un terzo dei casi contiene il solo marcatore, quindi `open: false` significa «l'ente non l'ha dichiarato lì», non «dato chiuso». `url` è il permalink `rel="alternate"` di tipo `text/html` della scheda sul portale, per citare la fonte senza ricostruire l'URL.
- `openrndt.record_license()` e `openrndt.record_url()` esposti come API di libreria.
- In `--format table` le tre colonne sono adattate alla lettura: `url` non viene stampata, `open` esce come sì/no e `license` è troncata a 60 caratteri. In `csv`, `compact` e `footprints` i valori restano interi.

### Fixed

- **`--bbox` è validata prima della chiamata di rete**: quattro valori numerici, longitudini fra -180 e 180, latitudini fra -90 e 90, `xmin < xmax`, `ymin < ymax`; in caso contrario uscita con codice 2 e messaggio esplicito. Il RNDT ignora in silenzio una bbox malformata e risponde con il catalogo intero: `--bbox "non,valido"` e `--bbox "12,45,11"` restituivano 23.738 record con codice 0, un falso successo per chi aveva chiesto una provincia.
- `codelists.py` documentava `AmbitoTerritoriale_s` con i valori `Provinciale` e `Comunale`, che in catalogo non esistono: i valori reali sono `Regionale`, `Nazionale` e `Locale` (più `Regional`/`Local` in inglese), e il campo manca sul 28% dei record. `discover --what lucene_fields` riportava quindi una codelist falsa.

### Note

L'header CSV cambia per l'aggiunta delle tre colonne: la modifica è additiva, chi legge per nome di colonna non è toccato, chi legge per posizione sì.

## [3.0.0] - 2026-08-09

### Changed

- **Rottura del formato di output**: negli output `table`, `csv`, `compact` e nelle proprietà del GeoJSON di `footprints`, il campo `updated` è ora `_source.apiso_Modified_dt` — la data della **scheda di metadato**, la stessa su cui filtrano `--updated-from`/`--updated-to`. L'istante di indicizzazione nel catalogo (`_source.sys_modified_dt`, che l'API espone come campo top-level `updated`) si chiama ora `indexed`. Prima le due grandezze condividevano il nome `updated`: si filtrava su un campo e se ne leggeva un altro, e un ordinamento per `apiso_Modified_dt:desc` mostrava una colonna scorrelata dall'ordine. Chi consuma `compact`/`csv`/GeoJSON deve rileggere il campo corretto; con `--format json` (payload grezzo dell'API) nulla cambia.
- La tabella del profilo `default` di `search` mostra anche la colonna `org` (`apiso_OrganizationName_txt`): `author` resta, ma contiene la sorgente di harvest (es. `csw.piemonte`), non l'ente responsabile.

### Added

- **`search --org` e `search --org-exact`** (anche su `footprints`): ricerca per ente responsabile. `--org` cerca la frase su `apiso_OrganizationName_txt`, campo analizzato e quindi case-insensitive e insensibile all'ordine dei token (`--org "comune di torino"` → 269 record, solo Comune di Torino); `--org-exact` fa il confronto esatto e case-sensitive su `EnteResponsabile_s`. Prima serviva scrivere la clausola Lucene a mano, e le forme più intuitive fallivano in silenzio.
- Su zero risultati con `--org`, la CLI esegue **una query esplorativa** e stampa i nomi di ente realmente presenti in catalogo che somigliano a quello cercato (l'API RNDT ignora il parametro `facet`, quindi l'aggregazione è a valle): `--org "comune di bologna"` → `Citta' metropolitana di Bologna | Regione Emilia-Romagna`, cioè chi pubblica davvero quei dati.
- La tabella di `search` porta in calce la legenda delle colonne data, e con `--format json` la CLI ricorda su stderr — solo quando la ricerca usa un filtro o un ordinamento sulle date — che nel payload grezzo `updated` è l'indicizzazione.
- `openrndt.record_dates()` e `openrndt.organization_names()` esposti come API di libreria, insieme a `compact_results()`.
- `search` e `footprints` con 0 risultati stampano su stderr **suggerimenti contestuali** (allargare `--q` con wildcard, rimuovere `--data-category`/`--time`/`--bbox`, ricerca per ente con `--org`, ricerca per territorio) invece del solo «Nessun risultato».
- Se l'API risponde con errore HTTP mentre è attivo `--sort`, il messaggio su stderr ricorda i campi ordinabili su RNDT (`title`, `apiso_Modified_dt`, forma `campo:asc|desc`) e rimanda a `discover --what sort_values`.
- `resources` accetta **più ID in batch** (`resources <id1> <id2> …`): health-check di un gruppo di metadati in un comando; gli errori per-record (`ItemNotFoundError`, HTTP, rete) producono una voce con `error` senza fermare gli altri. Con un solo ID il formato dell'output resta invariato.
- `resources --check` **segue i redirect** (max 3) ma solo verso **host pubblici**, con la stessa validazione dell'URL iniziale: l'endpoint ARPA Veneto catalogato in `http` (301→`https`) ora risulta `ok=true, redirected=true` invece del falso negativo `ok=false`; un redirect verso un host non pubblico non viene seguito ed espone `error=redirect-blocked:…`.
- `resources --check` riporta per ogni endpoint **`latency_ms`** (durata complessiva della probe) e i campi `redirected` / `redirect_count` / `redirect_url` (prima destinazione).

### Fixed

- **`latency_ms` di `resources --check` era sempre sbagliato**: la misura veniva presa in secondi ed emessa come millisecondi, quindi ogni probe sotto il mezzo secondo risultava `0` (live: WMS/WFS/download ISPRA tutti a `0`, ora 147/139/129 ms). Il test esistente passava anche col difetto: ora la durata è iniettata e il valore atteso è esatto.
- Il suggerimento su zero risultati indicava per gli enti il campo peggiore, `contact_organizations_s` con wildcard, descrivendolo come «esatto e case-sensitive»: quella forma restituisce 0 con la minuscola (`*bologna*`) e, con la maiuscola, centinaia di record di altri enti che semplicemente *nominano* quel territorio. Ora rimanda a `--org`.

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
