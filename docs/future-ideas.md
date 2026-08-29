# Idee future

Spunti raccolti per evoluzioni di openrndt. Non sono impegni: vanno valutati
caso per caso rispetto al design (CLI snella, read-only, niente cache locale).

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