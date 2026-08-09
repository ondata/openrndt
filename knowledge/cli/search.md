---
type: CLI Command
title: openrndt search
description: Cerca metadati nel RNDT con testo Lucene, bbox, categoria ISO 19115, intervalli temporali e ordinamento.
tags: [cli, search, lucene]
timestamp: 2026-08-09T00:00:00Z
---

Interroga l'endpoint [/rest/metadata/search](/api/rndt-rest-api.md) del RNDT.

# Opzioni

| Opzione | Significato |
|---------|-------------|
| `--q`, `-q` | Testo di ricerca, sintassi Lucene/Elasticsearch (AND implicito, `-termine`, `"frase"`, wildcard `*`/`?`, `campo:valore`, range su `_dt`/`_i`). |
| `--bbox` | Bounding box WGS84 `xmin,ymin,xmax,ymax`, semantica *overlaps*. |
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

# Comportamento ed errori

- 0 risultati con `--format` tabellare → avviso su stderr, exit 0.
- Parametri fuori range (`--num` > 5000, `--start` < 1) → messaggio leggibile, exit 2.
- Errore HTTP o di rete → messaggio self-contained su stderr, exit 1. Vedi [gestione errori](/conventions/error-handling.md).

Il passo successivo tipico è [get](/cli/get.md) sull'`id` scelto.
