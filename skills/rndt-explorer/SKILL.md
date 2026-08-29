---
name: rndt-explorer
description: >
  Esplorazione guidata del Repertorio Nazionale dei Dati Territoriali (RNDT)
  tramite la CLI openrndt. Usa questa skill ogni volta che l'utente cerca
  dati geografici, cartografici o territoriali italiani — anche se non
  menziona esplicitamente RNDT, geoportale o metadati. Coprono: catasto,
  cartografia di base, uso del suolo, idrografia, trasporti, ambiente,
  servizi WMS/WFS regionali e nazionali, dati INSPIRE, dataset ISTAT
  georeferenziati, dati di enti come Agenzia delle Entrate, ISPRA, regioni,
  comuni, autorità di bacino. La skill guida l'utente passo passo:
  scopre le codelist disponibili, esegue ricerche con filtri progressivi,
  recupera il dettaglio del metadato e segnala le risorse scaricabili
  (WMS, WFS, download diretto).
license: MIT
compatibility: >
  Richiede la CLI openrndt >= 3.1.0 (comandi: search, footprints, get,
  resources, discover).
  Installazione: `uv tool install openrndt` (da PyPI) oppure `uvx openrndt`.
metadata:
  author: ondata
  version: "3.2.0"
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
`open`, `license`, `url`, `resources` — ideale per individuare il record giusto prima
di chiedere il dettaglio con `get`. `open` e `license` sono ciò che l'ente ha dichiarato
in `isOpendata` (non normalizzato, e assente su una scheda su tre: vedi la nota più sotto),
`url` è il permalink citabile della scheda sul portale.
Se `resources` è `[]` il record non linka servizi fruibili: fai `get <id>` e
guarda `_source.links_s`.

**Le due date non sono la stessa cosa.** Negli output `compact`, `csv`, `table` e
`footprints`, `updated` è la data della **scheda** (`apiso_Modified_dt`) — la stessa
su cui filtrano `--updated-from/--updated-to` — mentre `indexed` è l'istante di
indicizzazione nel catalogo (`sys_modified_dt`), che non dice nulla né sul dato né
sulla scheda. Nel JSON grezzo (`--format json`) vale invece la convenzione
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
vedi [`references/search-syntax.md`](./references/search-syntax.md).

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

> **`isOpendata` non è l'elenco completo dei dati aperti.** Misurato su 3000 record il 2026-08-29: il
> campo è presente sul 72%, ma 1177 di quei record sono dell'Agenzia delle Entrate e senza di essi la
> copertura scende al 55%; in un terzo dei casi contiene solo il marcatore `opendata`, senza il nome
> della licenza. Alcuni dataset aperti hanno la licenza solo in `apiso_OtherConstraints_s` o in
> `apiso_ConditionApplyingToAccessAndUse_txt` e con `isOpendata:*` non si vedono. I valori inoltre non
> sono normalizzati: `CC BY 4.0`, `CCBY`, `Licenza CC-BY 4.0`, URL e interi paragrafi di disclaimer
> convivono nello stesso campo. Un conteggio dei dati aperti fatto su un solo campo non è difendibile:
> dichiara sempre quale campo hai usato.

**Operatori disponibili nel testo libero:**

```bash
# Esclusione con -
openrndt search --q "(suolo -natura)"

# Wildcard ovunque nel testo libero (* = zero o più char, ? = un char)
openrndt search --q "(*suo*)"
openrndt search --q "(na??ra)"          # matcha "natura", "navara", …

# Combinazione
openrndt search --q "(*suo* -na??ra)" --sort "title:desc"
```

**Regole wildcard per suffisso** (riverificate su API reale il 2026-08-29):

| Contesto | Wildcard trailing | Leading wildcard |
|---|---|---|
| Testo libero (senza `campo:`) | ✅ `palerm*` | ✅ `*palerm*` |
| Campo `_txt` (analizzato, case-insensitive) | ✅ `regione*` | ✅ `*egione*`, `*SICILIANA` |
| Campo `_s` (keyword, **case-sensitive**) | ✅ `Regione*` | ✅ `*Regione*`, `*Siciliana` |
| Campo `_dt` (data) | — | `[2024-01-01T00:00:00Z TO *]` |
| Campo `_i` (intero) | — | `[1 TO 10000]` |
| Campo `_b` (booleano) | — | `true` \| `false` |

> **Correzione**: una versione precedente di questa tabella dava il leading wildcard per bloccato sui
> campi con nome esplicito. Non lo è. Prova decisiva: `EnteResponsabile_s:*Siciliana` → 62, lo stesso
> totale della frase esatta `EnteResponsabile_s:"Regione Siciliana"`, mentre `EnteResponsabile_s:Siciliana`
> senza asterisco → 0. Se il `*` iniziale venisse scartato, la prima query varrebbe la terza e darebbe 0.
>
> Quando una wildcard su un campo `_s` dà 0, la causa quasi sempre è un'altra: quei campi sono
> case-sensitive. `EnteResponsabile_s:*siciliana` → 0, `EnteResponsabile_s:*Siciliana` → 62. Sui campi
> `_txt` la maiuscola è irrilevante: `apiso_OrganizationName_txt:*SICILIANA` → 62.

**Zero risultati? Leggi i suggerimenti su stderr.** Più spesso di quanto sembri, `0` è un esito legittimo, non un errore tuo. La CLI stampa suggerimenti contestuali: allarga il testo con wildcard, rimuovi `--data-category`/`--time`/`--bbox` uno alla volta, e cerca un ente col nominativo esatto. Tre cause ricorrenti:

- **Periodo senza record**: `--time 2024-01-01/2024-12-31` può restituire 0 perché in quel periodo non c'è nulla — allarga l'intervallo prima di concludere (vedi `workflows.md`).
- **Ente non presente in catalogo con quel nome**: `--org "comune di bologna"` → 0 perché quell'ente non pubblica in proprio (i suoi dati escono sotto Regione Emilia-Romagna o Città metropolitana). È il caso più frequente dopo i comuni capoluogo, e ha una sequenza sua: vedi «Cercare i dati di un ente che non pubblica in proprio» qui sotto.
- **Bbox ampia nei metadati**: molti record dichiarano bbox nazionali, quindi `--bbox` stretto li esclude — se serve «cosa copre la mia area» allarga il riquadro.

### Cercare i dati di un ente che non pubblica in proprio

Quando un comune non è in catalogo con il proprio nome, i suoi dati spesso ci sono lo stesso, caricati
dalla regione o dalla città metropolitana. Ordine dei tentativi, misurato sul caso Bologna il 2026-08-29:

1. **Gli enti che la CLI suggerisce.** Su zero risultati `--org` stampa i nomi realmente presenti che
   somigliano a quello cercato (`Citta' metropolitana di Bologna | Agenzia Regionale per La Sicurezza
   Territoriale | Regione Emilia-Romagna`). Rilancia `--org` su quelli: è la via più pulita, perché
   filtra per ente e non per testo.

2. **Il nome del territorio come frase esatta.** `--q '"Comune di Bologna"'` → 13 record, tutti
   pertinenti: sono i dati *di* quel territorio pubblicati da altri, e il nome compare nel titolo o
   nell'abstract. Poche righe, alta precisione: è il modo più rapido per capire se i dati esistono.

3. **Il nome del territorio più la sua bbox.** `--q "bologna" --bbox 11.25,44.44,11.42,44.55` → 1512
   record, i primi 20 tutti pertinenti. Serve quando il passo 2 è troppo stretto. In alternativa alla
   bbox, `--org` dell'ente sovraordinato: `--q "bologna" --org "Regione Emilia-Romagna"` → 1381.

**Due strade da non prendere**, entrambe verificate:

- `--bbox` più `AmbitoTerritoriale_s:Locale` non funziona come sembra. Il valore `Locale` copre 41
  record su un campione di 3000, e il filtro bbox è per sovrapposizione: i record a estensione
  nazionale passano comunque. Sulla bbox di Bologna quella query restituisce fogli geologici ISPRA
  del Monte Etna e di Caltanissetta.
- `contact_organizations_s:*Bologna*` → 110 record, e nessuno è del Comune: sono di Regione
  Emilia-Romagna, Città metropolitana, ARSTPC e ARPAE, cioè chi *nomina* quel territorio, spesso
  soltanto perché ci ha la sede legale. È anche case-sensitive: `*bologna*` → 0.

Se nessuna strada dà risultati, l'ente potrebbe davvero non avere dati in catalogo: è un esito
legittimo, non un errore della query.

**`--sort` che dà errore HTTP**: la CLI ricorda su stderr i campi ordinabili (solo `title` e `apiso_Modified_dt`, forma `campo:asc|desc`; `dateAscending`/`dateDescending`/`relevance` sono ignorati). Non insistere sul campo: filtra lato server e ordina lato client (vedi `search-syntax.md`).

---

## Fase 3 — Detail (singolo metadato)

Con un `id` interessante:

```bash
openrndt --format json get <id>           # JSON Elasticsearch (_source completo)
openrndt get <id> --xml > meta.xml         # XML ISO 19139 (per INSPIRE)
openrndt get <id> --html > meta.html       # HTML pronto
```

Struttura del payload e mappa dei campi `_source` (per costruire ricerche
mirate via `q=campo:valore`):
vedi [`references/result-structure.md`](./references/result-structure.md).

---

## Fase 4 — Download (risorse collegate)

I servizi e i file scaricabili stanno in `results[].links[]` (per ogni
risultato di `search`) o in `_source.links_s` / `_source.webServices_s`
(per `get`). Filtra per `dctype` (`WMS`, `WFS`, `WCS`, `download`).

Per estrazione e check veloce endpoint usa direttamente:

```bash
openrndt --format json resources <id>             # include ok/status_code/final_url
openrndt --format json resources <id> --no-check  # solo estrazione URL

# Health-check in batch: più ID in un comando (gli errori per-record non bloccano il resto)
openrndt --format json resources <id1> <id2> <id3>
```

Ogni riga del check riporta `ok`, `status_code`, `final_url`, `redirect_url`,
`redirected`/`redirect_count`, `latency_ms` e l'eventuale `error`:

- **I redirect vengono seguiti**, ma solo verso host pubblici: un endpoint
  catalogato in `http` che risponde 301 verso il suo equivalente `https`
  (es. `gaia.arpa.veneto.it`) ora risulta `ok=true` con `redirected=true`,
  non più falso negativo. Un redirect verso un host non pubblico (loopback,
  privato, DNS riservato) non viene seguito: `error=redirect-blocked:…`.
- **`latency_ms`** è la durata complessiva della probe: distingue un servizio
  vivo e veloce da uno 200 ma lento, che lo status da solo non dice.
- **Batch**: con più ID l'output JSON è `{"count": N, "results": [per-id]}`;
  un metadato mancante o irraggiungibile produce una voce con `error` senza
  interrompere gli altri (con un solo ID resta il formato storico).

Tabella `rel`/`dctype` completa in
[`references/result-structure.md`](./references/result-structure.md).

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

---

## Fase 5 — Visualizza (opzionale)

Il RNDT dice dove stanno i dati, non li mostra. Per guardarli senza aprire QGIS
si può usare [GeoLibre](https://geolibre.app), che ha una propria skill e un
proprio server MCP per scrivere progetti `.geolibre.json`. Tre cose diverse da
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
coordinate proiettate e non tutte le risorse sono leggibili da URL. La guida
completa - percorsi, ricette `jq`, pre-check con GDAL, tabella sintomo/causa e
`export_html` per condividere - è in
[`references/geolibre.md`](./references/geolibre.md).

---

## Workflow pronti

[`references/workflows.md`](./references/workflows.md) raccoglie sequenze
testate live (catasto per provincia, WMS di un tema INSPIRE, dataset di un
ente, aggiornamenti recenti per categoria, export CSV, dati scaricabili con
licenza e citazione della fonte per data journalist, sanity check con i
totali attesi).

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
