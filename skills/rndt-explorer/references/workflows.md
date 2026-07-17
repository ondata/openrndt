# Workflow tipici

Sequenze pronte da copiare. Tutte testate live su
`https://geodati.gov.it/RNDT` (numeri reali al 2026-05-27 in coda).

## 1. Catasto in provincia (filtro tematico + spaziale)

> "Trova i dataset catastali della provincia di Cuneo (bbox indicativa
> 7.0,44.0,8.5,45.0)."

```bash
# 1. categoria giusta (offline)
openrndt --format json discover --what data_categories | jq '.planningCadastre'
#   → "Pianificazione e catasto"

# 2. ricerca
openrndt --format json search \
  --q "catasto" \
  --data-category planningCadastre \
  --bbox 7.0,44.0,8.5,45.0 \
  --num 20

# 3. dettaglio del primo risultato
ID=$(openrndt --format json search --q "catasto" --data-category planningCadastre \
      --bbox 7.0,44.0,8.5,45.0 --num 1 | jq -r '.results[0].id')
openrndt --format json get "$ID" | jq '._source | {title, contact_organizations_s, INSPIRETheme_s}'

# 4. risorse scaricabili
openrndt --format json get "$ID" | jq -r '._source.links_s[]?'
```

## 2. Tutti i WMS di un tema INSPIRE

> "Lista degli endpoint WMS pubblicati nel RNDT per il tema INSPIRE
> Idrografia."

```bash
openrndt --format json search \
  --q 'INSPIRETheme_s:Idrografia' \
  --num 500 \
  | jq -r '.results[].links[]?
            | select(.dctype=="WMS") | .href' \
  | sort -u > wms-idrografia.txt
```

## 3. Cosa pubblica un ente specifico

> "Quali dataset risultano pubblicati dall'Agenzia delle Entrate?"

```bash
openrndt --format table search \
  --q 'contact_organizations_s:"Agenzia delle Entrate"' \
  --num 20 --sort 'apiso_Modified_dt:desc'
```

> ⚠️ Non usare `--sort dateDescending`: documentato sul RNDT ma **ignorato**
> dall'API (verificato live, riconfermato 2026-07-17). Il sort reale è
> `campo:asc|desc` — vedi [`search-syntax.md`](./search-syntax.md).

## 4. Aggiornamenti recenti

> "Dataset modificati nel 2024, dal più recente."

```bash
openrndt --format json search \
  --time "2024-01-01/2024-12-31" \
  --sort 'apiso_Modified_dt:desc' \
  --num 30
```

> ⚠️ **Limiti API noti**:
> 1. `--time` combinato con `--data-category` (o con qualsiasi `--q` su un
>    campo specifico tipo `keywords_s:…`) restituisce 0 risultati.
> 2. Il campo top-level `updated` di ogni risultato riflette la data di
>    reindicizzazione del catalogo (uguale per tutti), non la data del dataset.
>    Per ordinare/filtrare per "data del dataset" usare i campi `_source`:
>    - `apiso_Modified_dt` — dateStamp del metadato (il proxy più affidabile)
>    - `apiso_RevisionDate_dt` — data di revisione della risorsa (spesso null)
>    - `apiso_CreationDate_dt` — data di creazione (spesso null o fittizia)
>    - `timeperiod_nst[].begin_dt`/`end_dt` — copertura temporale dei dati
>      (è il campo su cui agisce il parametro `--time`)
>
>    Non esiste un campo `apiso_PublicationDate_dt` (verificato live 2026-07-17):
>    la data `publication` sta solo nell'XML ISO, non è indicizzata.
>
> Workaround per "inlandWaters revisionati nel 2024":
>
> ```bash
> openrndt --format json search --data-category inlandWaters --num 500 \
>   | jq '[.results[] | select(._source.apiso_RevisionDate_dt
>           and ._source.apiso_RevisionDate_dt >= "2024-01-01"
>           and ._source.apiso_RevisionDate_dt <  "2025-01-01")] | length'
> ```

## 5. Scarica l'XML ISO 19139 di un metadato

```bash
openrndt get age:D_E973_MARSAGLIA --xml > meta.xml
xmllint --noout meta.xml && echo "XML valido"
```

## 6. CSV per fogli di calcolo

```bash
openrndt --format csv search --q "ortofoto" --num 100 > ortofoto.csv
```

## 7. Dati scaricabili, licenza e citazione della fonte (data journalist)

> "Mi servono i dati sulla popolazione a rischio alluvioni, con licenza che
> ne permetta il riuso, e devo citare la fonte."

```bash
# 1. cerca solo open data, scrematura veloce con compact:
#    la colonna `resources` dice subito cosa offre ogni record
openrndt --format compact search --q "alluvioni AND isOpendata:*" --num 30
# {"id":"ispra_rm:01IdroHazard_DT","title":"Popolazione rischio alluvioni - Dataset",...,"resources":["WFS","WMS"]}

# 2. URL dei servizi con il tipo (usa `search --id`, che espone rel/dctype)
openrndt --format json search --id "ispra_rm:01IdroHazard_DT" \
  | jq -r '.results[0].links[] | select(.dctype != null) | "\(.dctype)\t\(.href)"'
# WMS   https://sdi.isprambiente.it/geoserver/nz1/wms?...
# WFS   https://sdi.isprambiente.it/geoserver/nz1/wfs?...

# 3. licenza, ente e data per la citazione della fonte
openrndt --format json get "ispra_rm:01IdroHazard_DT" \
  | jq '{licenza: ._source.isOpendata, ente: ._source.EnteResponsabile_s,
         aggiornato: ._source.apiso_Modified_dt}'
# → CC-BY-4.0, ISPRA, 2015-02-13

# 4. dal WFS ai dati tabellari (GeoPackage, apribile anche in QGIS)
ogr2ogr -f GPKG alluvioni.gpkg "WFS:https://sdi.isprambiente.it/geoserver/nz1/wfs" <feature_type>
```

Note verificate live (2026-07-17):

- `resources: []` nel compact è frequente: il record non linka servizi
  fruibili. In quel caso fai `get` e guarda `_source.links_s` — spesso il
  download è dietro un portale regionale (es. Geoscopio Toscana), non un
  link diretto.
- Il download diretto (`rel=enclosure` / `dctype=download`) è raro: la
  maggior parte dei dataset si prende via WFS (vettoriale) con `ogr2ogr` —
  vedi [`ogc-services.md`](./ogc-services.md).
- `isOpendata` può valere una licenza precisa (`"CC BY 4.0"`) o un generico
  `"opendata"`: per la licenza esatta guarda anche
  `_source.apiso_AccessConstraints_s`.

## Risultati di riferimento (sanity check)

Numeri ottenuti live al 2026-07-17 — utili per accorgersi di regressioni
(cambiano nel tempo: il catalogo cresce):

| Query                                                              | `total` atteso |
|--------------------------------------------------------------------|---------------:|
| `--q "catasto"`                                                    | 8.827          |
| `--data-category planningCadastre`                                 | 11.659         |
| `--data-category "planningCadastre,boundaries"`                    | 12.046         |
| `--q 'INSPIRETheme_s:Idrografia'`                                  | 863            |
| `--q 'contact_organizations_s:"Agenzia delle Entrate"'`            | 7.699          |
| `--q 'title:"carta geologica"'`                                    | 154            |
| catalogo completo (nessun filtro)                                  | 23.632         |
