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
| `sort`         | Ordinamento                                       | `dateAscending`, `dateDescending` (default), `relevance`, `title`; può ricevere suffisso `:desc` |
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

## Sort — valori validi

- `dateAscending` — data crescente
- `dateDescending` — data decrescente (default)
- `relevance` — pertinenza
- `title` — titolo

Suffisso `:desc` accettato (es. `sort=title:desc`).

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
