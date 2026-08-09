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
  --org "agenzia delle entrate" \
  --num 20 --sort 'apiso_Modified_dt:desc'
```

`--org` cerca la frase sul campo analizzato `apiso_OrganizationName_txt`: non
conta il maiuscolo né l'ordine dei token. Se conosci la stringa esatta in
catalogo usa `--org-exact "Agenzia delle Entrate"` (keyword, case-sensitive).

Se il risultato è 0, la CLI sonda il catalogo e stampa i nomi di ente presenti
che somigliano a quello cercato — molti comuni non pubblicano in proprio:

```bash
openrndt search --org "comune di bologna"
# → enti simili presenti in catalogo: Citta' metropolitana di Bologna | Regione Emilia-Romagna
```

Ripiego per territorio, quando l'ente non c'è (verificato: 15 record contro i
2.789 della sola bbox):

```bash
openrndt --format table search \
  --q 'AmbitoTerritoriale_s:Locale' --bbox 11.2,44.4,11.5,44.6 --num 20
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

Filtri data più espliciti (scheda vs pubblicazione):

```bash
openrndt --format json search \
  --q "catasto" \
  --updated-from 2024-01-01 --updated-to 2024-12-31 \
  --published-from 2020-01-01 \
  --num 30
```

> ⚠️ **Due correzioni a note precedenti** (riverificate live il 2026-07-18):
>
> 1. **`--time` combina correttamente con gli altri filtri.** Una nota precedente
>    lo dava per rotto ("in AND con `--data-category` restituisce 0"): era un
>    falso allarme, nato da uno *zero legittimo*. Verificato:
>    `--time 2015-01-01/2024-12-31 --data-category inlandWaters` → **42**;
>    `--time 2024-01-01/2024-12-31 --q 'keywords_s:"open data"'` → **52**
>    (esattamente i record attesi). Se una combinazione con `--time` dà 0,
>    prima di gridare al bug allarga l'intervallo: spesso nel periodo scelto
>    quei record semplicemente non esistono.
> 2. **`apiso_PublicationDate_dt` esiste**, contrariamente a quanto scritto
>    prima: è valorizzato su 8.402 dei 23.632 record ed è **filtrabile**
>    (non ordinabile). Vedi [`search-syntax.md`](./search-syntax.md).
>
> Resta vero invece che il campo top-level `updated` del **JSON grezzo** riflette
> l'istante di indicizzazione nel catalogo (`sys_modified_dt`, raggruppato per
> batch di reindicizzazione), non la data del dataset. Negli output
> `compact`/`csv`/`table`/`footprints` di openrndt quel valore si chiama
> `indexed`, e `updated` è invece `apiso_Modified_dt`. Per ragionare sulle date
> del dato usare i campi `_source`:
>
> - `apiso_Modified_dt` — dateStamp della scheda, unico ordinabile (100% dei record)
> - `apiso_RevisionDate_dt` — revisione della risorsa (56%)
> - `apiso_CreationDate_dt` — creazione della risorsa (43%)
> - `apiso_PublicationDate_dt` — pubblicazione della risorsa (36%)
> - `timeperiod_nst[].begin_dt`/`end_dt` — copertura temporale dei dati
>   (è il campo su cui agisce `--time`, e non è interrogabile via `--q`)

"inlandWaters con copertura temporale 2015-2024" — filtro lato server, niente `jq`:

```bash
openrndt --format json search --time "2015-01-01/2024-12-31" --data-category inlandWaters --num 100
```

## 5. Scarica l'XML ISO 19139 di un metadato

```bash
openrndt get age:D_E973_MARSAGLIA --xml > meta.xml
xmllint --noout meta.xml && echo "XML valido"
```

## 6. CSV per fogli di calcolo

```bash
openrndt --format csv search --q "ortofoto" --num 100 > ortofoto.csv
```

CSV più adatto a QGIS/script (URL servizi + bbox separata):

```bash
openrndt --format csv search --q "ortofoto" --profile qgis --num 100 > ortofoto_qgis.csv
```

## 7. Check rapido endpoint servizi di un metadato

```bash
# Estrai e verifica URL WMS/WFS/download
openrndt --format json resources age:D_E973_MARSAGLIA

# Solo estrazione (senza check HTTP)
openrndt --format json resources age:D_E973_MARSAGLIA --no-check
```

## 8. Footprint bbox in GeoJSON (QGIS / GeoPandas)

```bash
# Poligoni bbox per i primi 200 risultati
openrndt footprints --q "catasto" --num 200 > catasto_footprints.geojson

# Footprint già filtrati su area/tempo
openrndt footprints \
  --bbox 11.2,44.4,11.5,44.6 \
  --updated-from 2024-01-01 \
  --num 200 > bologna_footprints.geojson
```

## 9. Dati scaricabili, licenza e citazione della fonte (data journalist)

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
