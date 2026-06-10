# RNDT REST API — riferimento ufficiale

Pagina di origine: <https://geodati.gov.it/geoportale/eng/strumenti-en/rest-api>
Data acquisizione: 2026-05-27.

## URL base

```
https://geodati.gov.it/RNDT/rest/metadata/search?<parametro>&<parametro>&…
```

## Parametri

| Parametro      | Descrizione                                      | Valori |
|----------------|--------------------------------------------------|--------|
| `q`            | Testo di ricerca                                  | stringa Lucene/Elasticsearch (campi indicizzati, wildcard, booleani) |
| `bbox`         | Estensione geografica (ovest,sud,est,nord)        | `xmin,ymin,xmax,ymax` in WGS84 |
| `dataCategory` | Categoria tematica (ISO 19115 TopicCategoryCode) — **vedi nota sotto** | uno o più valori separati da virgola |
| `time`         | Intervallo temporale                              | `yyyy-mm-dd` (inizio/fine) |
| `sort`         | Ordinamento — **vedi nota sotto**                 | sintassi reale <code>campo:asc&#124;desc</code> (es. `apiso_Modified_dt:desc`). `dateDescending`/`dateAscending` documentati ma **non ordinano** |
| `start`        | Numero primo record (1-based)                     | intero |
| `num`          | Numero massimo risultati                          | intero, max 5000, default 10 |
| `f`            | Formato risposta                                  | `atom`, `json`, `json-source`, `csw`, `rss`, `csv`, `kml`, `eros` |
| `id`           | ID del metadato                                   | stringa (es. `ispra_rm:0029CNATHB_DT`) |

## ⚠️ Nota — `dataCategory` non filtra

Verifica live del 2026-05-27:

```bash
# Catalogo totale
curl ".../search?f=json&num=1"                              # total = 23580
# Stesso totale, "filtro" ignorato
curl ".../search?dataCategory=planningCadastre&f=json&num=1"# total = 23580
# Filtro reale, via campo Elasticsearch keywords_s
curl ".../search?q=keywords_s:planningCadastre&f=json&num=1"# total = 11351
```

La pagina ufficiale elenca `dataCategory` tra i parametri ma sull'endpoint
`https://geodati.gov.it/RNDT/rest/metadata/search` **il parametro non
applica alcun filtro**. Per filtrare per categoria ISO 19115 occorre usare
il parametro `q` con la sintassi Lucene sul campo indicizzato `keywords_s`:

- `q=keywords_s:planningCadastre`
- `q=keywords_s:(planningCadastre OR boundaries)` per più categorie.

La CLI `openrndt` traduce automaticamente `--data-category VAL[,VAL2]` in
questa clausola, componendola in AND con un eventuale `--q` esplicito.

Non risulta documentato come issue né sulla pagina ufficiale né nello
Swagger di `gpt.geocloud.com`.

## ⚠️ Nota — `sort`: i valori `dateDescending`/`dateAscending` non ordinano

Verifica live (2026-06-10), cross-validata anche sull'endpoint di test Esri
(`gpt.geocloud.com/geoportal3`):

```bash
# Stesso ordine identico → il sort per data "amichevole" è ignorato
curl ".../search?q=apiso_Type_s:dataset&sort=dateDescending&num=3"  # id: MARSAGLIA, SARDEG, MESERO
curl ".../search?q=apiso_Type_s:dataset&sort=dateAscending&num=3"   # id: MARSAGLIA, SARDEG, MESERO (identici)
```

Il meccanismo di ordinamento che **funziona** è la sintassi Elasticsearch
`campo:asc|desc` su un campo *sortable*:

```bash
# Ordina davvero per data di modifica del metadato
curl ".../search?q=apiso_Type_s:dataset&sort=apiso_Modified_dt:desc&num=3"  # 2026-06-05, 2026-05-28, …
curl ".../search?q=apiso_Type_s:dataset&sort=apiso_Modified_dt:asc&num=3"   # 1988-10-05, 2000-01-01, …
```

Regole verificate:

- Sortable: campi keyword (`_s`), data (`_dt`), intero (`_i`).
- Ordinare per un campo `text`/analizzato (es. `sort=title` nudo) dà errore
  Elasticsearch: *"Fielddata is disabled on [title]… Please use a keyword field instead."*
- `relevance` funziona (ordina per pertinenza).
- **Non esiste un campo data-di-pubblicazione ordinabile.** Le varianti
  `apiso_PublicationDate_dt`, `apiso_Date_dt`, ecc. sono assenti dall'indice.
  Mapping date verificato: `apiso_RevisionDate_dt` = ISO `dateType=revision`,
  `apiso_Modified_dt` = dateStamp del metadato, `apiso_CreationDate_dt` spesso
  `null` o fittizio (`2012-01-01`). La data di pubblicazione esiste **solo**
  nell'XML (`gmd:CI_Date` con `dateType=publication`), non come campo indicizzato.
- Proxy pratico per "ultimi pubblicati/aggiornati": `sort=apiso_Modified_dt:desc`.

## ⚠️ Nota — il servizio CSW non ordina (`SortBy` ignorato)

Endpoint CSW: `https://geodati.gov.it/RNDT/csw` (OGC CSW 2.0.2 ISO AP).
Verifica live (2026-06-10): l'elemento `<ogc:SortBy>` viene **completamente
ignorato**. Una `GetRecords` con `SortProperty` `apiso:Modified`, `apiso:Title`
o `apiso:PublicationDate`, in `ASC` o `DESC`, restituisce sempre gli stessi
record nello stesso ordine di default (MARSAGLIA, SARDEG, MESERO):

```bash
curl -X POST -H 'Content-Type: application/xml' --data @query.xml \
  'https://geodati.gov.it/RNDT/csw'
# <ogc:SortBy><ogc:SortProperty>
#   <ogc:PropertyName>apiso:PublicationDate</ogc:PropertyName>
#   <ogc:SortOrder>DESC</ogc:SortOrder>
# </ogc:SortProperty></ogc:SortBy>  → ordine invariato
```

Questo viola la INSPIRE *Technical Guidance for the implementation of INSPIRE
Discovery Services v3.1*, che richiede il supporto dell'ordinamento (`SortBy`)
nel servizio di discovery CSW.

## Formati output

| Sigla         | Formato |
|---------------|---------|
| `atom`        | Atom Feed |
| `json`        | JSON |
| `json-source` | JSON sorgente (Elasticsearch `_source` grezzo) |
| `csw`         | Catalog Service Web (XML OGC) |
| `rss`         | RSS Feed |
| `csv`         | Comma Separated Values |
| `kml`         | KML |
| `eros`        | Formato proprietario |

## Endpoint dettaglio item

Verificati live (2026-05-27, HTTP 200):

- `GET /RNDT/rest/metadata/item/{id}` → JSON Elasticsearch (`_source` completo).
- `GET /RNDT/rest/metadata/item/{id}/xml` → XML ISO 19139 (`gmd:MD_Metadata`).
- `GET /RNDT/rest/metadata/item/{id}/html` → HTML.

## Esempi ufficiali

### 1. Ricerca per tema INSPIRE

```
https://geodati.gov.it/RNDT/rest/metadata/search?q=INSPIRETheme_s:Idrografia&start=1&num=300&f=json&sort=title
```

### 2A. Frase esatta nel titolo

```
https://geodati.gov.it/RNDT/rest/metadata/search?q=title:"carta geologica"&start=20&num=50&f=html&sort=title:desc
```

### 2B. Termine nel titolo + termine ovunque

```
https://geodati.gov.it/RNDT/rest/metadata/search?q=(title:carta geologica)&start=20&num=50&f=html&sort=title:desc
```

### 2C. AND booleano

```
https://geodati.gov.it/RNDT/rest/metadata/search?q=title:(carta AND geologica)&start=20&num=50&f=html&sort=title:desc
```

### 3A. Inclusione + esclusione

```
https://geodati.gov.it/RNDT/rest/metadata/search?q=(suolo -natura)&start=1&num=50&f=json&sort=title:desc
```

### 3B. Wildcard

```
https://geodati.gov.it/RNDT/rest/metadata/search?q=(*suo* -na??ra)&start=1&num=50&f=json&sort=title:desc
```

- `*` → zero o più caratteri.
- `?` → esattamente un carattere.

### 4. Per ID

```
https://geodati.gov.it/RNDT/rest/metadata/search?id=ispra_rm:0029CNATHB_DT
```

## ⚠️ Nota — `found: false` su ID inesistente

L'endpoint `/rest/metadata/item/{id}` risponde sempre **HTTP 200**, anche
quando l'ID non esiste. Il body contiene `"found": false` invece di un
codice 404. Esempio:

```json
{"_index": "geoportal-metadata_v1", "_id": "id_inesistente", "found": false}
```

La CLI `openrndt` controlla esplicitamente `found` e solleva `ItemNotFoundError`,
producendo un messaggio leggibile su stderr invece di restituire silenziosamente
un oggetto senza `_source`.

## ⚠️ Nota — link `alternate` nel JSON di `get` puntano a IP interno

I link di navigazione nel JSON dell'endpoint item (`links[].href` con
`rel: "alternate"`) puntano a un IP interno del server RNDT:

```
http://192.168.3.34:8080/geoportal-catalog/rest/metadata/item/...
```

I link ai servizi reali (WMS, WFS, download) presenti in `_source.links_s`
sono corretti e pubblici. Usare quelli per navigazione e download effettivi.
Il bug è lato server e non è documentato ufficialmente.

## Note tecniche

- Motore di ricerca: Elasticsearch su Apache Lucene.
- Sintassi query: <https://lucene.apache.org/core/2_9_4/queryparsersyntax.html>.
- Trucco pratico: usare la Ricerca Dettagliata del portale web, impostare i filtri, copiare l'URL della pagina di anteprima per imparare la sintassi.
