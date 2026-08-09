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
  Richiede la CLI openrndt (comandi: search, footprints, get, resources, discover).
  Installazione: `uv tool install openrndt` (da PyPI) oppure `uvx openrndt`.
metadata:
  author: ondata
  version: "1.2"
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
campi ad alto segnale — `id`, `title`, `org`, `type`, `category`, `updated`, `resources` —
ideale per individuare il record giusto prima di chiedere il dettaglio con `get`.
Se `resources` è `[]` il record non linka servizi fruibili: fai `get <id>` e
guarda `_source.links_s`.

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
# Per ente/organizzazione (non esiste flag --organization)
openrndt search --q "apiso_OrganizationName_txt:\"Regione Siciliana\""

# Solo open data (isOpendata contiene la licenza, non un booleano)
openrndt search --q "isOpendata:*"                    # qualunque open data
openrndt search --q "isOpendata:\"CC BY 4.0\""        # licenza specifica

# Per tema INSPIRE
openrndt search --q "INSPIRETheme_s:\"Parcelle catastali\""

# Aggiornati dopo una data
openrndt search --q "apiso_RevisionDate_dt:[2024-01-01T00:00:00Z TO *]"

# Per tipo risorsa
openrndt search --q "apiso_Type_s:service"
```

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

**Regole wildcard per suffisso** (verificate su API reale):

| Contesto | Wildcard trailing | Leading wildcard |
|---|---|---|
| Testo libero (senza `campo:`) | ✅ `palerm*` | ✅ `*palerm*` |
| Campo `_txt` (analizzato) | ✅ `palerm*` | ❌ bloccato |
| Campo `_s` (keyword, case-sensitive) | ✅ `Palerm*` | ❌ bloccato |
| Campo `_dt` (data) | — | `[2024-01-01T00:00:00Z TO *]` |
| Campo `_i` (intero) | — | `[1 TO 10000]` |
| Campo `_b` (booleano) | — | `true` \| `false` |

> Il leading wildcard è bloccato solo quando si specifica un campo esplicito (`campo:*valore*`). Sul testo libero funziona.

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
```

Esempio rapido — tutti i WMS dei primi 50 risultati di una ricerca:

```bash
openrndt --format json search --q "catasto" --num 50 \
  | jq -r '.results[].links[]? | select(.dctype=="WMS") | .href' \
  | sort -u
```

Tabella `rel`/`dctype` completa in
[`references/result-structure.md`](./references/result-structure.md).

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
`--bbox-crs`, `--updated-*`, `--published-*`) e restituisce una
`FeatureCollection` con proprietà essenziali (`id`, `title`, `org`, `type`,
`updated`, `resources`).

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
