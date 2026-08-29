# Idee future

Spunti raccolti per evoluzioni di openrndt. Non sono impegni: vanno valutati
caso per caso rispetto al design (CLI snella, read-only, niente cache locale).

## Ponte verso la visualizzazione: openrndt + GeoLibre (2026-08-29)

Test riuscito: dal record RNDT `r_emiro:2016-04-01T154419` a due layer WMS visibili in GeoLibre Desktop,
con `openrndt` per la ricerca e il server MCP `geolibre-mcp` per scrivere il `.geolibre.json`. Quattro
chiamate MCP: `create_project`, due `add_ogc_layer`, `describe_project`.

Sei cose che il ponte deve fare da solo, tutte verificate sul campo:

1. **Ricavare il nome del layer.** `add_ogc_layer` richiede `layers`, che RNDT non fornisce: il record dà
   il `GetCapabilities` dell'intero server. Su quel WMS ci sono sei annate (1853, 1976, 1994, 2003, 2008,
   2011) dietro un solo record di catalogo. Il nome però è ricavabile dal primo link del metadato, nella
   forma GeoNode `/layers/<workspace>:<layer>`. Senza questo passaggio il percorso resta manuale, e sul
   server ARPA Veneto ha richiesto due tentativi e un timeout prima di trovare il layer giusto.

2. **Promuovere l'endpoint a https.** RNDT cataloga molti servizi in `http` (ARPA Veneto risponde 301
   verso `https`). Le tile in `http` non arrivano nemmeno a partire: la webview di GeoLibre le blocca in
   1-4 millisecondi, con `status 0` e un messaggio generico su CORS/TLS che manda fuori strada. Il server
   in questo caso mandava header CORS corretti in entrambi gli schemi: la causa è solo lo schema. Con
   `https` gli stessi due layer si vedono.

3. **Provare una GetMap prima di aprire la mappa.** Un `GetCapabilities` che risponde 200 non garantisce
   che il server disegni. Serve una tile vera su un bbox del dato, e va guardata: su un catalogo dove il
   63% dei record non linka nulla e alcuni endpoint rispondono 500, una mappa bianca senza spiegazione
   costa più del controllo.

4. **Scrivere i bounds di ogni layer.** `wms_layer` di GeoLibre non popola mai `source.bounds` (lo fa solo `tile_layer`), quindi il layer WMS arriva nel progetto senza estensione dichiarata e lo «zoom to fit» dell'app non ha su cosa inquadrare: non succede nulla. L'estensione c'è in due posti - il `BoundingBox CRS:84` di ciascun layer nel `GetCapabilities`, e la bbox del record RNDT - e va copiata nel progetto come `source.bounds = [west, south, east, north]`. Attenzione: su un source raster MapLibre `bounds` limita anche le richieste di tile, quindi un `GetCapabilities` che dichiara un'estensione più stretta del dato reale fa sparire ciò che sta fuori. Meglio la bbox dichiarata dal servizio per quel layer che quella del record, che copre l'intero servizio.

5. **Leggere i metadati della risorsa con GDAL prima di aggiungerla.** GeoLibre legge le risorse con GDAL (in-browser, via duckdb-wasm), quindi lo stesso `ogrinfo`/`gdalinfo` che gira in locale è il controllo preventivo che dice se la risorsa sarà leggibile, e vale per i file come per i servizi. Un caso reale: uno shapefile zippato di Citta Metropolitana di Firenze risponde 200 in https con CORS `*`, e in locale `ogrinfo /vsizip/file.zip` lo legge - ma da URL fallisce, perché il server risponde 200 all'intero file anche a una richiesta `Range` e `/vsizip//vsicurl/` ha bisogno delle range request per leggere la coda dell'archivio. In GeoLibre l'errore arriva come «GDAL Error (4): ... does not exist in the file system», che non dice nulla della causa; `ogrinfo "/vsizip//vsicurl/<url>"` in locale dà invece «Range downloading not supported by this server!». Stesso comando, stessa risposta del browser, prima di scrivere il progetto. Sul PPR della Regione Piemonte (206, `Accept-Ranges`, CORS `*`) lo stesso controllo passa e restituisce 189 punti in EPSG:32632. Quando il controllo fallisce, la risorsa va scaricata e servita in altro modo, non puntata per URL.

6. **Scrivere lo swipe con quattro voci, non due.** Il tool `add_swipe` del server MCP registra su ogni lato l'id del layer di progetto, e per due layer WMS non basta: lo swipe che ne esce mostra lo stesso layer su entrambe le meta'. Un layer WMS esiste con due identificatori - l'uuid del layer e l'id dello style MapLibre `layer-<uuid>-raster` - e una configurazione che funziona li tiene incrociati: a sinistra l'uuid del layer di sinistra piu' lo style-id di quello di destra, a destra l'uuid del layer di destra piu' lo style-id di quello di sinistra. Ricavato da un progetto salvato dall'app dopo aver configurato lo swipe a mano, non dedotto: leggere il file salvato dall'app resta il modo piu' affidabile di scoprire come si scrive una parte di progetto che il server MCP non copre.

Il progetto scritto porta in `metadata` la provenienza: id del record, link alla scheda, ente, servizio.
Con i campi `url` e `org` aggiunti alla CLI nella 3.1.0 viene gratis, ed è ciò che rende una mappa citabile.

Forma da decidere: una «Fase 5 - visualizza» dentro `rndt-explorer`, oppure una skill a sé che faccia da
ponte fra le due. La prima tiene insieme il percorso di chi cerca dati; la seconda non obbliga chi usa
`rndt-explorer` ad avere GeoLibre.

## Comando `which`: dall'intento al comando (2026-08-29)

Preso da `ars-sicilia-pp-cli which "cerca un atto per numero" --json`, che restituisce i comandi
candidati con `command`, `description`, `group`, `why_it_matters` e uno `score`.

Qui il valore non sarebbe scegliere fra cinque comandi, che si leggono in un `--help`: sarebbe
scegliere fra **strategie e trappole**, che è dove un agente sbaglia davvero. Le risposte utili le
abbiamo già misurate e documentate, mancherebbe solo esporle come dati interrogabili:

| Intento | Rotta | `why_it_matters` |
|---|---|---|
| «cosa pubblica il comune X» | `search --org` | Se dà 0, l'ente non pubblica in proprio: nomi suggeriti dalla CLI, poi la frase esatta del territorio. Non `contact_organizations_s:*X*`, che pesca chi lo nomina. |
| «solo dati aperti» | `search --q "isOpendata:*"` più il campo `license` | Copre il 72% dei record (55% senza Agenzia delle Entrate) e in un terzo dei casi è il solo marcatore: alcune schede aperte hanno la licenza solo in `apiso_OtherConstraints_s`. |
| «i più recenti» | `--sort apiso_Modified_dt:desc` | È la data della scheda, non del dato. `apiso_PublicationDate_dt` filtra ma non ordina, `dateDescending` è ignorato. |
| «cosa copre quest'area» | `search --bbox` o `footprints` | Il filtro è per sovrapposizione: i record a estensione nazionale passano sempre. |
| «per categoria tematica» | `--data-category` | Il parametro ufficiale `dataCategory` non filtra: la CLI traduce in `keywords_s:VAL`. |
| «portalo in QGIS» | `resources` poi `ogr2ogr` | Gli URL sono `GetCapabilities` dell'intero server: il nome del layer va ricavato dal link GeoNode del record. |

Forma: `openrndt which "<frase>"`, offline come `discover`, `--json` per gli agenti, corrispondenza
lessicale su una tabella di intenti in `codelists.py` (niente modelli, niente dipendenze). Le voci
`why_it_matters` sono già scritte in `knowledge/api/known-issues.md` e nella skill: il lavoro è
raccoglierle in un unico punto interrogabile invece di sperare che l'agente legga la skill giusta.

Da valutare rispetto al design snello: aggiunge un comando che non interroga il RNDT. L'argomento a
favore è che oggi quelle trappole si evitano solo se l'agente ha caricato la skill, e in questa
stessa sessione si è visto che il caricamento per nome può risolvere sulla copia sbagliata.

## Spunti dalla valutazione v2.0.0 (2026-08-09)

Dalla verifica live con scenari per tecnici GIS, analisti e uffici comunali
(dettagli in `docs/evaluation-v2.0.0.md`):

### Ricerca per ente (`--org` / `--suggest-org`)

Punto debole verificato: `apiso_OrganizationName_txt:"Comune di Bologna"` → 0
(testo analizzato), `EnteResponsabile_s`/prefisso IPA → 0 (comune non
indicizzato con quei nomi), wildcard su `contact_organizations_s` → over-match.
Proposta: flag `--org <nome>` che cerca in OR sui campi ente (con
`--org-exact` per la stringa esatta), oppure `--suggest-org` che stampa i
valori distinti che matchano il testo per scoprire la stringa giusta. Non tocca
i dati a monte, solo il lato query.

### Zero risultati e query invalide parlanti

Su `total=0` suggerire percorsi alternativi (es. ricerca per territorio con
`--bbox`); su `--sort` che genera HTTP 500 stampare i campi ordinabili (già
disponibili offline in `discover --what sort_values`).

### `resources` batch e con latenza

Oggi accetta un solo ID e riporta solo lo status (HEAD). Per valutare i
servizi di una ricerca intera servono argomenti multipli; per distinguere un
servizio vivo da uno lento serve il tempo di risposta della probe, non il solo
200.

### Tabella `--wide`

Le colonne title/bbox/org vengono troncate in terminali stretti. Opzione per
non troncare o per scegliere le colonne.

## Spunti da Copernicus-Services-Products-Metadata

Riferimento: <https://github.com/do-me/Copernicus-Services-Products-Metadata>

Quel progetto fa l'opposto di openrndt — snapshot statico settimanale del
catalogo committato nel repo (Parquet/CSV/Excel/JSON) + discovery locale
**retrieve-then-rerank** con cross-encoder. openrndt invece è live e read-only.
Le idee trasferibili:

### Rerank semantico sui risultati (priorità alta)

La ricerca lessicale RNDT (Solr/Lucene) premia chi ripete le parole esatte
della query. Un reranker leggero — es. `cross-encoder/ettin-reranker-17m-v1`
(~68 MB, gira su CPU) — potrebbe riordinare i top-N di `openrndt search` per
*intento* anziché per match testuale.

- Flag opzionale `--rerank` su `search`: prende i top-K, costruisce
  "product documents" compatti (titolo + abstract + keyword) e li riordina.
- Resta opzionale → non rompe il design read-only.
- Dipendenza pesante: valutare extra `pip install openrndt[rerank]` oppure
  tenerla fuori dalla CLI e solo dentro la skill.
- Da verificare: qualità del reranker in italiano (serve un PoC su query reale).

### Snapshot periodico + cronologia (GitHub Actions)

Workflow CI separato (NON nella CLI) che fa un dump periodico del catalogo RNDT.
Abilita: ricerca offline veloce, rerank senza N chiamate di rete, e soprattutto
il **diff temporale** ("cosa è stato aggiunto/modificato nel catalogo questo
mese"). Da tenere come artefatto di repo, fuori dal design no-cache della CLI.

### Output Parquet per analisi

Aggiungere `--format parquet` (preserva i tipi, ottimo per duckdb/pandas).
Coerente con l'uso analitico, basso costo. Unico formato extra che aggiunge
valore reale rispetto a json/table/csv già presenti.

### Output compatto per agenti AI — ✅ implementato

Realizzato come `--format compact` (NDJSON, una riga per record). Vedi PR #7.
Nota di design: in Copernicus il "product document" sintetico è costruito
*prima* di cercare (catalogo locale); in openrndt il catalogo è remoto, quindi
il formato compatto è solo un rendering dei risultati *dopo* la `search`.

## Da NON fare

- Snapshot dentro la CLI: violerebbe il design read-only/no-cache. Va come
  workflow separato.
- Replicare i 6 formati di output di Copernicus: ridondante. Solo Parquet
  aggiunge valore reale.
 ## Spunti da pi-ogh-summer-school-2026

Riferimento: <https://codeberg.org/leandro-parente/pi-ogh-summer-school-2026>

Skill per l'agente Pi (OpenGeoHub Summer School 2026): da una richiesta in linguaggio naturale su dati di osservazione della Terra sceglie il provider, cerca nel catalogo STAC e **consegna uno script loader pronto** in una delle 6 lingue supportate. Progetto lontano da openrndt — multi-provider, con autenticazione, su dati raster — ma tre scelte di design sono trasferibili.

### Snippet eseguibili come deliverable (priorità alta)

L'idea forte: il risultato utile non è il metadato, è il codice che apre il dato. `--profile qgis` emette già i campi che uno snippet interpolerebbe (`wms_url`, `wfs_url`, `download_url`, `xmin..ymax`); manca il passo che li trasforma in comando eseguibile.

L'asse giusto per RNDT **non è il linguaggio** ma lo *strumento consumatore*: QGIS, `ogr2ogr`, geopandas/owslib, DuckDB spatial, R `sf`. Circa 5 template, non 24. I 24 di pi-ogh sono 6 lingue × 4 provider: debito di manutenzione dettato dal pubblico di una summer school, che chiede anche Julia e C++.

Collocazione: `skills/rndt-explorer/templates/` (oggi esiste solo `references/`). Anche pi-ogh ha scelto skill e non estensione per la stessa ragione — serve generazione di codice con gli strumenti esistenti, non nuova macchineria richiamabile dall'LLM.

Decisione aperta: se invece diventasse un comando (`openrndt snippet <id> --for qgis`), per convenzione di progetto va sviluppato in parallelo su CLI e libreria Python, con test e README. Impegno molto diverso.

### Stimare prima, non scaricare mai per verificare

pi-ogh ha una regola esplicita: la validazione è ricerca + asset raggiungibile + eventuale finestra di pochi pixel; il caricamento completo non si esegue mai, si stima la dimensione (bbox ÷ area pixel).

In openrndt la parte di probe è già coperta da `resources --check` (batch, `latency_ms`, redirect, dalla v3.0.0). Manca la regola a valle: **stimare il numero di feature prima del download** (WFS `resultType=hits`, `GetCapabilities`) e scrivere nelle Rules della skill che non si fa `ogr2ogr` sull'intero servizio per capire se è vivo.

### Due dettagli a costo quasi zero

- **Colonna di onestà nelle tabelle dei template**: pi-ogh marca ogni riga con `✅ verificato dal vivo` oppure `non testato qui (manca R)`. Rende leggibile a colpo d'occhio cosa è provato e cosa è scritto a memoria.
- **«Mai inventare un ID»**: loro impongono di elencare o grepare il catalogo prima di usare un id di collezione. Analogo in una riga: mai inventare un campo Lucene o un codice categoria, prima `discover`.

### Cosa non si trasferisce

- Template multi-linguaggio (6 lingue): l'asse sbagliato, vedi sopra.
- Gestione credenziali per provider: RNDT è aperto.
- Immagine Docker da 14 GB con Python/R/Julia/Rust preinstallati.
- **Routing table multi-provider dentro la CLI**: fuori perimetro, il design è read-only e single-portal. A livello di *skill* è legittima solo nella forma minima: quando RNDT è il catalogo sbagliato, rimandare a `ckan-explorer`, `situas-explorer`, `portolan`. 