---
name: rndt-explorer
description: >
  Esplorazione guidata del Repertorio Nazionale dei Dati Territoriali (RNDT), il
  catalogo nazionale dei metadati geografici italiani (ISO 19115/INSPIRE), tramite
  la CLI openrndt. Usa questa skill ogni volta che l'utente cerca dove trovare dati
  geografici, cartografici o territoriali italiani, anche senza menzionare RNDT o
  geoportale: identifica i dataset, l'ente che li pubblica davvero, la data del
  dato, la licenza dichiarata e i servizi fruibili (WMS, WFS, download diretto).
  Copre catasto e temi INSPIRE, cartografia di base, uso del suolo, idrografia,
  rischi, trasporti, ambiente, confini amministrativi. Non usarla per: geodati non
  italiani (Copernicus, Corine), statistiche o tabelle senza geometrie,
  elaborazione di file GIS che l'utente ha già, portali open data non geografici
  (CKAN, dati.gov.it), codici ISTAT senza geometrie, audit di qualità dei dati,
  contatti e PEC degli enti, o per navigare il portale di un singolo ente.
license: MIT
compatibility: >
  Richiede la CLI openrndt >= 3.3.1 (comandi: search, footprints, get,
  resources, discover). Dalla 3.3.0 `get` emette il documento normalizzato e
  accetta `--raw`, dalla 3.3.1 `get`, `resources` e `search --id` accettano un
  UUID senza prefisso: con una CLI precedente le ricette che li usano falliscono.
  Installazione: `uv tool install openrndt` (da PyPI) oppure `uvx openrndt`.
metadata:
  author: ondata
  version: "3.4.7"
---

# RNDT Explorer — esplorazione guidata del catalogo

Questa skill usa la **CLI openrndt** per interrogare il
[Repertorio Nazionale dei Dati Territoriali](https://geodati.gov.it/RNDT/),
catalogo ufficiale italiano dei metadati geografici (ISO 19115/19139).

L'opzione **globale** `--format` (sempre PRIMA del comando) sceglie l'output:

```bash
openrndt --format json search …    # default, per parsing
openrndt --format table search …   # Rich, per umani
openrndt --format csv search …     # per fogli di calcolo
openrndt --format compact search … # NDJSON: 1 riga/record, per scremare a basso costo
```

Il formato `compact` (solo per `search`) emette una riga JSON per record con i
campi ad alto segnale — `id`, `title`, `org`, `type`, `category`, `updated`, `indexed`,
`open`, `license`, `url`, `resources`, `email`, `download` — ideale per individuare
il record giusto prima di chiedere il dettaglio con `get`. `open` e `license` sono ciò
che l'ente ha dichiarato in `isOpendata` (non normalizzato, e assente su una scheda su
tre: vedi la nota più sotto), `url` è il permalink citabile della scheda sul portale,
`email` è il punto di contatto designato e `download` gli URL di download dichiarati
(`url_download_s` + `url_http_download_s`, esposti come sono).
Se `resources` è `[]` o `download` è `[]` il record non linka servizi fruibili: fai
`get <id>` e guarda il suo campo `resources`, che parte da `resources_nst` (i tipi
assegnati dal catalogo) e ricade sui link solo dove quello manca.

**Le tre date non sono la stessa cosa.** Negli output `compact`, `csv`, `table` e
`footprints`, `updated` è la data della **scheda** (`apiso_Modified_dt`) — la stessa
su cui filtrano `--updated-from/--updated-to` — mentre `indexed` (presente in
`compact`, `footprints` e nei profili `gis`/`qgis`, non nel `csv`/`table` di default)
è l'istante di indicizzazione nel catalogo (`sys_modified_dt`), che non dice nulla né
sul dato né sulla scheda. La data del **dato** è una terza cosa: sta in
`apiso_RevisionDate_dt` / `apiso_CreationDate_dt` / `apiso_PublicationDate_dt`
(vedi Fase 3 per sapere quale delle tre è compilata su un record). Nel JSON grezzo (`--format json`) vale invece la convenzione
dell'API: il campo top-level `updated` è quello di **indicizzazione**, la data
della scheda sta in `_source.apiso_Modified_dt`.

Per output tabellari/CSV di `search` puoi usare anche preset:

```bash
openrndt search ... --profile gis            # senza --format esce già in table
openrndt --format csv search ... --profile qgis
```

- `--profile gis`: colonne essenziali per analisi rapida (tipo/categoria/ente/risorse/bbox).
- `--profile qgis`: colonne pronte per flussi QGIS/script (`wms_url`, `wfs_url`, `download_url`, `xmin..ymax`).
- `--profile` con `--format json` o `compact` espliciti non si applica: la CLI lo dice su stderr e lascia l'output invariato.

Altre opzioni globali (sempre PRIMA del comando): `--timeout <secondi>` per il
timeout HTTP per singolo tentativo (default 30s; con i retry il caso peggiore è
~3x — utile abbassarlo se il portale è lento), `--base-url` per un mirror,
`--version` (o `-V`) per sapere quale versione della CLI è installata.

Tutti i comandi hanno `--help`. La skill segue 4 fasi.

---

## Fase 1 — Discovery (offline, sempre prima)

Scopri le codelist valide **senza chiamate di rete**:

```bash
openrndt --format json discover                                # tutto
openrndt --format json discover --what data_categories         # ISO 19115
openrndt --format json discover --what sort_values
openrndt --format json discover --what output_formats
openrndt --format json discover --what search_params
openrndt --format json discover --what lucene_fields           # campi Lucene
```

Dettaglio delle categorie ISO 19115 e cheat sheet
"bisogno → categoria" in [`references/categories.md`](./references/categories.md).

---

## Fase 2 — Search (filtri progressivi)

Parti stretto, poi allarga. La ricerca minima:

```bash
openrndt --format json search --q "catasto" --num 10
```

Filtri principali:

| Flag CLI            | Filtra su                                                  |
|---------------------|------------------------------------------------------------|
| `--q`               | testo, sintassi Lucene/Elasticsearch                        |
| `--bbox`            | bounding box WGS84 `xmin,ymin,xmax,ymax`                    |
| `--bbox-crs`        | CRS dichiarato bbox: accetta `EPSG:4326`, `CRS:84`, `WGS84` (niente reproiezione) |
| `--data-category`   | categoria ISO 19115 (es. `planningCadastre`)                |
| `--org`             | ente responsabile, frase su `apiso_OrganizationName_txt` (analizzato: case-insensitive, ordine dei token irrilevante) |
| `--org-exact`       | ente responsabile, confronto esatto e case-sensitive su `EnteResponsabile_s` |
| `--time`            | range temporale della **risorsa** `yyyy-mm-dd/yyyy-mm-dd`   |
| `--modified`        | range modifica del **record nel catalogo** `yyyy-mm-dd/yyyy-mm-dd` |
| `--updated-from/--updated-to` | range data aggiornamento scheda (`apiso_Modified_dt`) |
| `--published-from/--published-to` | range data pubblicazione (`apiso_PublicationDate_dt`) |
| `--sort`            | <code>campo:asc&#124;desc</code> su campo sortable (es. `apiso_Modified_dt:desc`). `dateDescending`/`dateAscending` **non ordinano**. `apiso_Modified_dt` è la data della *scheda*, non dei *dati* — vedi "Quale data stai ordinando" in [`references/search-syntax.md`](./references/search-syntax.md) |
| `--start --num`     | paginazione (1-based, max `num`=5000)                       |
| `--id`              | recupera un solo metadato per ID                            |
| `--profile`         | preset colonne output `table/csv`: `default`, `gis`, `qgis`; senza `--format` implica `table` |

> **Importante**: il parametro `dataCategory` documentato sul RNDT **non
> filtra**; la CLI traduce internamente `--data-category` in
> `q=keywords_s:VAL`. Dettagli in `ref/rest-api-rndt.md`.

Sintassi `--q` (AND/OR/NOT, frasi esatte, wildcard, campi specifici):
vedi [`references/search-syntax.md`](./references/search-syntax.md). **Lo spazio fra
termini è un OR**, non un AND: `catasto siciliana` (8.903) vale `catasto OR siciliana`,
mentre `catasto AND siciliana` dà 1. Se aggiungendo una clausola il totale *cresce*, è
questo. Scrivi sempre `AND` esplicito per restringere. (`discover --what search_params`
delle versioni ≤ 3.1.0 della CLI dice «AND implicito»: è sbagliato, corretto dalla 3.2.0.)

**Ricerca per campo** — usa `campo:valore` in `--q`. I campi interrogabili
sono visibili con `openrndt discover --what lucene_fields`. Esempi utili:

```bash
# Per ente/organizzazione: usa --org, non scrivere la clausola a mano
openrndt search --org "regione siciliana"

# Solo open data (isOpendata contiene la licenza, non un booleano)
openrndt search --q "isOpendata:*"                    # dichiarati open data: 16.759
openrndt search --q "isOpendata:\"CC BY 4.0\""        # licenza specifica: 10.534

# Per tema INSPIRE
openrndt search --q "INSPIRETheme_s:\"Parcelle catastali\""

# Aggiornati dopo una data
openrndt search --q "apiso_RevisionDate_dt:[2024-01-01T00:00:00Z TO *]"

# Per tipo risorsa
openrndt search --q "apiso_Type_s:service"
```

**Conteggi difendibili.** Prima di pubblicare un numero, dichiara il campo licenza
che hai usato (`isOpendata` copre il 72% delle schede e in un terzo dei casi ha solo
il marcatore, quindi non è l'elenco dei dati aperti) e misura il rumore dentro il
perimetro: allargarlo fa entrare fuori tema. Ricette e nota completa su `isOpendata`
in [`references/workflows.md`](./references/workflows.md) §11.

**Wildcard**: funzionano ovunque, anche iniziali e anche su campo esplicito
(`EnteResponsabile_s:*Siciliana` → 62). Se una wildcard su un campo `_s` dà 0, di
norma è la maiuscola: quei campi sono case-sensitive, i `_txt` no. Tabella per
suffisso, operatori del testo libero ed esempi in
[`references/search-syntax.md`](./references/search-syntax.md).

**Zero risultati? Leggi i suggerimenti su stderr.** Più spesso di quanto sembri, `0` è un esito legittimo, non un errore tuo. La CLI stampa suggerimenti contestuali: allarga il testo con wildcard, rimuovi `--data-category`/`--time`/`--bbox` uno alla volta, e cerca un ente col nominativo esatto. Tre cause ricorrenti:

- **Periodo senza record**: `--time 2024-01-01/2024-12-31` può restituire 0 perché in quel periodo non c'è nulla — allarga l'intervallo prima di concludere (vedi `workflows.md`).
- **Ente non presente in catalogo con quel nome**: `--org "comune di bologna"` → 0 perché quell'ente non pubblica in proprio (i suoi dati escono sotto Regione Emilia-Romagna o Città metropolitana). È il caso più frequente dopo i comuni capoluogo, e ha una sequenza sua: vedi «Cercare i dati di un ente che non pubblica in proprio» qui sotto.
- **Bbox ampia nei metadati**: molti record dichiarano bbox nazionali, quindi `--bbox` stretto li esclude — se serve «cosa copre la mia area» allarga il riquadro.

### Cercare i dati di un ente che non pubblica in proprio

Un comune assente dal catalogo con il proprio nome quasi sempre ha i suoi dati
lì lo stesso, caricati dalla regione o dalla città metropolitana. Quattro passi,
in ordine: gli enti che la CLI suggerisce su zero risultati, il nome del
territorio come frase esatta, il nome più la bbox (o `--org` dell'ente
sovraordinato), e infine l'aggregazione per ente di una ricerca sul solo nome
(`--format compact … | jq -r .org | sort | uniq -c`), che è il passo che chiude
la risposta: «chi pubblica davvero» è quell'elenco, non il primo ente trovato.
Cita sempre `id` o `url` delle schede: una tabella di soli titoli non è
verificabile. Sequenza estesa, numeri misurati e due strade da non prendere in
[`references/workflows.md`](./references/workflows.md) §12.

### Da un toponimo al bbox

`--bbox` vuole coordinate: per un comune, una frazione o una località usa
Nominatim (OpenStreetMap) con **una** chiamata, non web search o scraping di siti
aggregatori (lenti, fragili, non ufficiali). Nominatim restituisce il bbox come
`[lat_min, lat_max, lon_min, lon_max]`: va riordinato in `xmin,ymin,xmax,ymax`.

Per `search --bbox` non geocodificare indirizzi o civici: l'estensione dei
metadati RNDT è un rettangolo grossolano (regione, provincia, comune o area fra
più enti), quindi la scala della via non ha senso per il catalogo e aggiunge solo
un punto di rottura (nomi di via degli atti diversi da OSM, civici assenti).
Parti dal comune o dalla frazione.

Dopo, per interrogare un servizio del dataset trovato, la via torna utile: il WFS
catastale dell'Agenzia delle Entrate si interroga solo per bbox (non per foglio o
particella), quindi per scaricare le particelle attorno a un indirizzo serve
geocodificarlo. Se il civico non c'è, geocodifica la via; se non si trova, prova
il nome senza secondi nomi o titoli (in OSM «Via Padre Annibale Di Francia», non
«Via Padre Annibale Maria di Francia»).

```bash
B=$(curl -s -A "openrndt-skill" \
  "https://nominatim.openstreetmap.org/search?q=Morghen,Ceppo+Morelli&format=jsonv2&limit=1&countrycodes=it" \
  | jq -r '.[0].boundingbox as [$s,$n,$w,$e] | "\($w),\($s),\($e),\($n)"')
openrndt --format compact search --bbox "$B" --q "\"Ceppo Morelli\""
# → age:D_C478_CEPPO_MORELLI  Cartografia catastale - Comune di CEPPO MORELLI
```

Regole d'uso di Nominatim: massimo una richiesta al secondo, User-Agent che
identifica l'applicazione (non dati personali dell'utente), niente geocodifica
massiva. Controlla `addresstype` (`hamlet`, `village`, …) e il nome del comune nel
risultato: toponimi uguali in regioni diverse sono frequenti. Se serve il perimetro
ufficiale di una località, la fonte è ISTAT (località abitate), non OSM.

**`--sort` che dà errore HTTP**: la CLI ricorda su stderr i campi ordinabili (solo `title` e `apiso_Modified_dt`, forma `campo:asc|desc`; `dateAscending`/`dateDescending`/`relevance` sono ignorati). Un campo sconosciuto (`--sort description`) non dà errore: viene ignorato in silenzio e l'ordine resta quello del no-sort, quindi controlla che i primi id cambino davvero. Non insistere sul campo: filtra lato server e ordina lato client (vedi `search-syntax.md`).

---

## Fase 3 — Detail (singolo metadato)

L'ID del catalogo è `prefisso:uuid` (es. `r_sicili:7832b30d-…`): `get`, `resources` e `search --id` risolvono da soli un UUID nudo via ricerca; se corrisponde a più schede ricevi un errore esplicito con i candidati.

Con un `id` interessante:

```bash
openrndt --format json get <id>           # documento normalizzato (_source in coda)
openrndt get <id> --raw                    # sola busta Elasticsearch (ante 3.3.0)
openrndt get <id> --xml > meta.xml         # XML ISO 19139 (per INSPIRE)
openrndt get <id> --html > meta.html       # HTML pronto
```

Il documento normalizzato ha in cima i campi già pronti - `data_date` (la data
del **dato**), `contact` (`{name, email, website}`), `bbox`, `lineage`,
`resources`, `open`/`license`, `url` - e in coda `_source` inalterato. Prima di
ricostruire un valore a mano da `_source`, controlla se è già al primo livello.

Struttura del payload e mappa dei campi `_source` (per costruire ricerche
mirate via `q=campo:valore`):
vedi [`references/result-structure.md`](./references/result-structure.md).

**Quale data è "la data del dato"? Lo dice solo l'XML.** Il JSON espone
`apiso_RevisionDate_dt`, `apiso_CreationDate_dt`, `apiso_PublicationDate_dt` già
separati, ma quando su un record ne compare una sola non dice quale ruolo avesse
nella scheda originale, e `apiso_Modified_dt` è la data della scheda, non del dato.
Se devi scrivere «aggiornato il …» in un documento, conferma il tipo con l'XML,
dove ogni data porta il suo `CI_DateTypeCode`:

```bash
openrndt get <id> --xml | grep -A3 "<gmd:date>" | grep -E "gco:Date|codeListValue"
```

**Scegli la scheda giusta fra i duplicati.** Lo stesso oggetto può avere più
record: l'Agenzia delle Entrate ha schede comunali del 2021 senza licenza standard
(«dato pubblico CAD, oneroso per i privati») accanto a schede 2025 con `CC BY 4.0`
e WMS+WFS, e una serie madre `age:S_0000_ITALIA`. Prima di descriverne uno, guarda
i candidati in `compact` ordinati per `apiso_Modified_dt:desc` e prendi il più
recente, o dichiara perché no.

---

## Fase 4 — Download (risorse collegate)

Per un record singolo la via breve è il campo `resources` di `get`: già
tipizzato e deduplicato, identico a `resources --no-check`. Le fonti grezze
restano disponibili - `results[].links[]` per ogni risultato di `search`,
`_source.links_s` / `_source.webServices_s` dentro la busta - e lì si filtra per
`dctype` (`WMS`, `WFS`, `WCS`, `download`).

Per estrarre gli endpoint e provarli usa `resources`.

**Attenzione alle chiavi: `resources` e `links` non usano gli stessi nomi.** In
`search`/`get` ogni voce di `links[]` ha `dctype` e `href`; nell'output di
`resources` la stessa risorsa ha `type` e `url` (più `source`). Un `jq` con
`select(.dctype=="WMS") | .href` su `resources` restituisce `null` e sembra un
servizio rotto: è solo la chiave sbagliata.

```bash
openrndt --format json resources <id>             # include ok/status_code/final_url
openrndt --format json resources <id> --no-check  # solo estrazione URL

# chiavi giuste per resources: .type e .url
openrndt --format json resources <id> | jq -r '.resources[] | "\(.type)\t\(.url)"'
# con più id l'output è {"count":N,"results":[…]}: .results[].resources[]

# Health-check in batch: più ID in un comando (gli errori per-record non bloccano il resto)
openrndt --format json resources <id1> <id2> <id3>
```

Ogni riga riporta `ok`, `status_code`, `final_url`, `redirect_url`,
`redirected`/`redirect_count`, `latency_ms` e l'eventuale `error`. I redirect
sono seguiti solo verso host pubblici, e con più ID gli errori per-record non
fermano gli altri. Campi in dettaglio e tabella `rel`/`dctype` in
[`references/result-structure.md`](./references/result-structure.md).

**`ok=true` vuol dire «il GetCapabilities risponde», non «il servizio serve mappe».**
Il WMS PCN della Carta Geologica risponde 200 al GetCapabilities e `ServiceException`
a ogni GetMap (il MapServer non raggiunge il proprio database). Prima di mettere un
WMS in una pagina o in un report come "funzionante", chiedi una tile vera e controlla
che torni `image/*` (ricetta in [`references/ogc-services.md`](./references/ogc-services.md),
«Il GetCapabilities vivo non basta»). Nella direzione opposta, fino alla CLI 3.1.0 un
server con TLS legacy (`sgi2.isprambiente.it`) dava `ConnectError` pur rispondendo a
curl: se `error` è di rete, riprova con `curl -sI` prima di dichiararlo morto.

Esempio rapido — tutti i WMS dei primi 50 risultati di una ricerca:

```bash
openrndt --format json search --q "catasto" --num 50 \
  | jq -r '.results[].links[]? | select(.dctype=="WMS") | .href' \
  | sort -u
```

Una volta ottenuto l'endpoint di un servizio OGC (WMS/WFS/WCS/WMTS),
esploralo con GDAL/OGR a output JSON (`gdalinfo -json "WMS:…"`,
`ogrinfo -json "WFS:…"`): nomi dei layer, feature type, quali layer sono
interrogabili con GetFeatureInfo, download vettoriale con `ogr2ogr`. Guida in
[`references/ogc-services.md`](./references/ogc-services.md).

---

## Export footprint GeoJSON (QGIS-ready)

Per portare rapidamente i risultati su mappa (QGIS/GeoPandas), esporta le bbox
dei metadati come poligoni GeoJSON (EPSG:4326):

```bash
openrndt footprints --q "catasto" --num 100 > footprints.geojson
```

Il comando accetta gli stessi filtri principali di `search` (inclusi
`--bbox-crs`, `--org`, `--updated-*`, `--published-*`) e restituisce una
`FeatureCollection` con proprietà essenziali (`id`, `title`, `org`, `type`,
`updated`, `indexed`, `open`, `license`, `url`, `resources`).

Due cose da sapere prima di aprirlo in QGIS: `resources` è un array, e QGIS lo
legge male come attributo (appiattiscilo con `jq` in una stringa `WMS;WFS`); e il
filtro `--bbox` è per **sovrapposizione**, quindi i record a estensione nazionale
o mondiale passano sempre (su «uso del suolo» in Sicilia: 82 record, 1 solo
siciliano). Per separare locale/regionale/nazionale usa la ricetta fissa in
[`references/workflows.md`](./references/workflows.md) §10, invece di inventare
soglie ogni volta.

---

## Fase 5 — Visualizza (opzionale)

Il RNDT dice dove stanno i dati, non li mostra. Per guardarli senza aprire QGIS
si può usare [GeoLibre](https://geolibre.app), che ha una propria skill e un
proprio server MCP per scrivere progetti `.geolibre`. Tre cose diverse da
mettere su mappa, con comandi e limiti diversi:

- **dove stanno i dataset trovati**: `openrndt footprints` produce il GeoJSON
  delle bbox, che diventa un layer classificabile (per esempio per distinguere
  i record con risorse collegate da quelli senza);
- **il dato visto attraverso un servizio**: un WMS del record diventa un layer,
  due annate dello stesso tema diventano uno swipe;
- **il dato vero**: un WFS in `application/json` o un file scaricabile letto
  direttamente dal suo URL.

Il passaggio non è automatico: il nome del layer non sta nel metadato, molti
endpoint sono catalogati in `http`, un WFS senza `srsName` risponde in
coordinate proiettate, un layer WMS nasce senza estensione e va corredato a mano
di `source.bounds` o lo «zoom to fit» non lo raggiunge, non tutte le risorse
sono leggibili da URL, e GeoLibre
(MapLibre) scarica le tile con `fetch`: il server WMS deve rispondere con **un
solo** header `Access-Control-Allow-Origin`. Un servizio che a curl dà 200 può
fallire in pagina con `Failed to fetch (0)` (visto sull'ArcGIS ISPRA, che manda
due header): non è un difetto di GeoLibre né tuo, e una pagina Leaflet, che carica
le tile come `<img>`, lo mostra comunque. Tre consegne,
scelte in base a cosa deve poterci fare chi riceve: il file progetto
`.geolibre` (la fonte, per chi ha l'app), la pagina di `export_html` (che
non è una figura ma l'applicazione dentro una pagina: l'altro può aggiungere
layer, confrontare, interrogare, senza installare nulla) e un URL
`web.geolibre.app/?url=…` o `?data=…` a un progetto o a un GeoJSON
che pubblichi tu su un host con CORS (l'URL diretto a un WFS di un ente funziona
per l'11,6% dei link del catalogo, quasi tutti Sardegna e Bolzano); il progetto si
conserva sempre. In tutte e tre i layer li scarica il browser di chi guarda: un
WMS/WFS senza CORS non si vede in nessuna. La guida
completa - percorsi, ricette `jq`, pre-check con GDAL, tabella sintomo/causa e
le tre consegne - è in
[`references/geolibre.md`](./references/geolibre.md).

---

## Workflow pronti

[`references/workflows.md`](./references/workflows.md) raccoglie sequenze
testate live (catasto per provincia, WMS di un tema INSPIRE, dataset di un
ente, aggiornamenti recenti per categoria, export CSV, dati scaricabili con
licenza e citazione della fonte per data journalist, footprint per area con le
soglie di estensione §10, conteggio difendibile e nota completa su `isOpendata`
§11, ente che non pubblica in proprio §12, sanity check con i totali attesi).

## Output e parsing

Quando usare json/table/csv/xml/html:
[`references/output-formats.md`](./references/output-formats.md).

## Il catalogo in QGIS / GDAL (CSW)

Il RNDT espone anche un servizio CSW, utile **solo** per portare il catalogo
dentro un flusso GIS (layer vettoriale con geometria bbox, export `ogr2ogr`,
QGIS MetaSearch). Per cercare — testo, data, area, ente, licenza — e per
ordinare, l'API REST è migliore su ogni criterio, filtro spaziale incluso.
Ricette testate e limiti del servizio in
[`references/csw.md`](./references/csw.md).

## Riferimenti esterni

- Doc ufficiale: <https://geodati.gov.it/geoportale/eng/strumenti-en/rest-api>
- Cartella `ref/` del progetto: spec API completa e nota sui bug osservati.
