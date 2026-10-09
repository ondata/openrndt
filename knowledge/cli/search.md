---
type: CLI Command
title: openrndt search
description: Cerca metadati nel RNDT con testo Lucene, bbox, categoria ISO 19115, intervalli temporali e ordinamento.
tags: [cli, search, lucene]
timestamp: 2026-10-04T00:00:00Z
---

Interroga l'endpoint [/rest/metadata/search](/api/rndt-rest-api.md) del RNDT.

# Opzioni

| Opzione | Significato |
|---------|-------------|
| `--q`, `-q` | Testo di ricerca. Le parole di testo libero sono unite in **AND** (vedi `--q-mode`). Una `q` con sintassi Lucene passa intatta, e lì l'API usa l'**OR implicito** fra termini separati da spazio: per restringere scrivere `AND`. Sintassi riconosciuta: `-termine`, `"frase"`, wildcard `*`/`?`, `campo:valore`, range su `_dt`/`_i`). |
| `--q-mode` | Come la CLI costruisce la clausola testo: `all` (default) unisce le parole in AND con escape dei caratteri speciali Lucene, tenendo le wildcard `*`/`?`; `any` le unisce in OR (il comportamento dell'API fino alla 3.3.1); `lucene` passa la `q` intatta. In `all` e `any` una `q` che contiene `:`, virgolette, parentesi, `AND`/`OR`/`NOT`, un `-`/`+` a inizio parola, fuzzy (`termine~1`) o boost (`termine^2`) passa comunque intatta. In `all` e `any` le parole senza lettere né cifre (il ` - ` di un titolo incollato, `–`, `/`) sono scartate: in AND diventavano un termine che nessuna scheda contiene e azzeravano la ricerca (#32); una `q` fatta solo di questi segni è un errore. Un valore di `--q-mode` non valido è un errore anche senza `--q`. Motivo: con l'OR dell'API `copertura del suolo` trovava 23.820 record, l'intero catalogo; in AND ne trova 1.415 ([known-issues](/api/known-issues.md)). |
| `--bbox` | Bounding box WGS84 `xmin,ymin,xmax,ymax`, semantica *overlaps*. Validata prima della chiamata: quattro valori numerici, longitudini in -180..180, latitudini in -90..90, `xmin < xmax`, `ymin < ymax`. Una bbox malformata esce con codice 2 e non interroga l'API, che la ignorerebbe restituendo il catalogo intero. |
| `--bbox-crs` | CRS esplicito della bbox. Supportati: `EPSG:4326` (default implicito), `CRS:84`, `WGS84`. |
| `--org` | Ente responsabile: frase su `apiso_OrganizationName_txt` (campo analizzato, quindi case-insensitive e insensibile all'ordine dei token). In AND con gli altri filtri. Su zero risultati la CLI fa una query esplorativa e stampa i nomi di ente presenti in catalogo che somigliano a quello cercato. |
| `--org-exact` | Ente responsabile in forma esatta e case-sensitive su `EnteResponsabile_s`. Alternativo a `--org`. |
| `--data-category`, `-c` | Una o più categorie ISO 19115 separate da virgola (es. `planningCadastre`). Tradotta internamente in `keywords_s:VAL` perché il parametro ufficiale `dataCategory` [non filtra](/api/known-issues.md). |
| `--time` | Intervallo temporale della risorsa `yyyy-mm-dd/yyyy-mm-dd`. |
| `--modified` | Intervallo di modifica del record nel catalogo (diverso da `--time`). |
| `--updated-from` / `--updated-to` | Intervallo data aggiornamento metadato (campo `apiso_Modified_dt`) in formato `yyyy-mm-dd`. |
| `--published-from` / `--published-to` | Intervallo data pubblicazione (campo `apiso_PublicationDate_dt`) in formato `yyyy-mm-dd`. |
| `--sort` | `campo:asc\|desc` su campo sortable, es. `apiso_Modified_dt:desc`. I valori documentati `dateDescending`/`dateAscending` [NON ordinano](/api/known-issues.md). |
| `--start` | Indice 1-based del primo record (default 1). |
| `--num`, `-n` | Numero massimo di record (default 10, max 5000). |
| `--id` | Filtra per ID metadato specifico. |
| `--profile` | Preset colonne per output `table`/`csv`: `default`, `gis` (campi essenziali) o `qgis` (URL servizi + bbox in colonne separate). Se `--format` non è indicato, l'output passa da solo a `table`; con `--format json` o `compact` espliciti il preset non si applica e la CLI avvisa su stderr. |

# Examples

```bash
# Ricerca semplice, output JSON
openrndt search -q "uso del suolo" -n 5

# Scrematura a basso costo di token per un agente (NDJSON)
openrndt --format compact search -c planningCadastre -n 50

# Ultimi metadati aggiornati in una bbox (area Bologna)
openrndt search --bbox 11.2,44.4,11.5,44.6 --sort apiso_Modified_dt:desc -n 10

# Ricerca con data aggiornamento e pubblicazione
openrndt search --q "catasto" --updated-from 2024-01-01 --published-from 2020-01-01 -n 20

# Profilo GIS per lettura umana (senza --format esce già in tabella)
openrndt search --q "catasto" --profile gis -n 20

# Profilo QGIS per CSV pronto a join/uso in plugin o script
openrndt --format csv search --q "catasto" --profile qgis -n 20

# Cosa pubblica un ente
openrndt search --org "comune di torino" -n 20

# Query Lucene su campo specifico
openrndt search -q 'apiso_OrganizationName_txt:ispra AND isOpendata:*'
```

# Campi data negli output

Negli output `table`, `csv` e `compact`:

- `updated` = `_source.apiso_Modified_dt`, la data della **scheda di metadato**: lo stesso campo su cui filtrano `--updated-from`/`--updated-to` e l'unico valorizzato sul 100% del catalogo;
- `indexed` = `_source.sys_modified_dt`, l'istante di **indicizzazione nel catalogo**: è il valore che l'API espone come campo top-level `updated`, raggruppato per batch di reindicizzazione.

Con `--format json` l'output è il payload grezzo dell'API e vale la convenzione dell'API: `updated` top-level è l'indicizzazione. La CLI lo ricorda su stderr quando la ricerca usa un filtro o un ordinamento sulle date.

# Link a GeoLibre

Dalla 3.5.0 ogni record porta `geolibre_url`, subito dopo `url`: `https://web.geolibre.app/?plugin=openrndt-geolibre&rndt=<id>`, con l'id codificato per l'URL (`:` → `%3A`). Apre il record in GeoLibre web dentro il plugin [openrndt-geolibre](https://github.com/ondata/openrndt-geolibre), e a chi non ha il plugin GeoLibre lo propone con «Trust and load». È in `compact`, `csv`, nei profili `gis` e `qgis`, e anche nel JSON grezzo, aggiunto a ogni risultato (è l'unica chiave che la CLI aggiunge al payload dell'API). In `table` esce, come `url`. Funziona su web.geolibre.app, non ancora in GeoLibre Desktop 3.2.0 né con `layout=viewer` (opengeos/GeoLibre#2898). Lo costruisce una sola funzione, `geolibre_url()` in `search.py`, usata anche da [get](/cli/get.md) e [footprints](/cli/footprints.md).

# Comportamento ed errori

- 0 risultati con `--format` tabellare → avviso su stderr, exit 0.
- Parametri fuori range (`--num` > 5000, `--start` < 1) → messaggio leggibile, exit 2.
- Errore HTTP o di rete → messaggio self-contained su stderr, exit 1. Vedi [gestione errori](/conventions/error-handling.md).

Il passo successivo tipico è [get](/cli/get.md) sull'`id` scelto.
