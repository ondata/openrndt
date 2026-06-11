# Esplorare i servizi OGC del catalogo RNDT

Gran parte dei metadati RNDT linka **servizi OGC** — WMS, WFS, WCS, WMTS
(campo `links`, `dctype`). Questo riferimento è di servizio all'esplorazione di
quei servizi: una volta ottenuto l'endpoint con `openrndt get`, ispezionalo per
capire cosa offre (layer, feature type, interrogabilità, dati scaricabili)
prima di usarlo.

Strumento di elezione: **GDAL/OGR con output JSON**, perché dà info strutturate
e affidabili. Regola generale valida per qualunque servizio OGC, non solo quelli
del RNDT: **non andare a memoria sui nomi dei layer, interroga il servizio**.

Parsa sempre con `jq` e azzera lo stderr (`2>/dev/null`): i warning GDAL
sporcano lo stdout JSON.

## Il GetCapabilities ha TUTTO

Ogni servizio OGC si auto-descrive con il documento **GetCapabilities**: è la
fonte autorevole e completa. Contiene tutto ciò che serve a usare il servizio:

- elenco dei layer / feature type / coverage, con `Name`, `Title`, `Abstract`;
- per i WMS: l'attributo `queryable="0|1"` (interrogabilità con GetFeatureInfo),
  gli **stili** disponibili, i **formati** immagine e i formati di
  GetFeatureInfo, i limiti di **scala** (`MinScaleDenominator`/`Max…`);
- i **CRS/SRS** supportati e i **bounding box** per ciascun layer;
- per i WFS: i formati di output (`outputFormat`), le operazioni supportate.

Richiesta (sostituisci `SERVICE`/`VERSION` per WFS/WCS/WMTS):

```bash
curl -s "<endpoint>?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities" -o caps.xml
```

GDAL/OGR ne leggono solo un **sottoinsieme comodo** (nomi + titoli, come layer
raster/vettoriali pronti all'uso) e scartano il resto. Quindi: usa GDAL per la
via rapida, ma quando ti serve un'informazione che GDAL non espone
(queryability, stili, scale, formati) vai **sempre** al GetCapabilities nativo.

## Esplorare un WMS — `gdalinfo -json`

Elenca i layer come *subdataset* (parsing del GetCapabilities):

```bash
gdalinfo -json "WMS:<endpoint>?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities" 2>/dev/null \
  | jq -r '.metadata.SUBDATASETS | to_entries[] | select(.key|endswith("_DESC")) | .value'
```

Ogni subdataset ha solo due chiavi:

- `SUBDATASET_N_NAME` → un URL **GetMap** (è GDAL che traduce ogni layer in
  una richiesta GetMap; per questo il subdataset non è un GetCapabilities).
- `SUBDATASET_N_DESC` → il **titolo** del layer.

## Esplorare un WFS — `ogrinfo -json`

Elenca i *feature type* (layer vettoriali):

```bash
ogrinfo -json "WFS:<endpoint>" 2>/dev/null | jq '[.layers[].name]'
```

## Cosa GDAL NON dà: `queryable` e abstract

`gdalinfo -json` espone **solo** Nome (come GetMap) e Titolo. **Non** porta i
flag di capability del WMS (`queryable`, `opaque`, stili) né l'abstract: per
design li scarta. Verificato e confermato dalla doc GDAL (driver WMS) e dalla
community: *"the NAME is used as `_NAME`, the TITLE for `_DESC`… user need to
read the [resto] directly from the native GetCapabilities response"*.

### Quali layer sono interrogabili con GetFeatureInfo?

Sta **solo** nel GetCapabilities XML, attributo `<Layer queryable="0|1">`.
GDAL non lo espone. Lettura diretta:

```bash
curl -s "<endpoint>?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities" -o caps.xml
grep -n -A2 '<Layer queryable=' caps.xml | grep -E 'queryable=|<Name>'
```

Il primo `<Name>` dopo ogni `<Layer queryable="…">` è il nome del layer (lo
`<Name>` con `default` che segue appartiene allo `<Style>`, ignoralo).

## Interrogare un punto (GetFeatureInfo) — `gdallocationinfo`

GDAL *sa* fare una GetFeatureInfo, ma con un altro strumento: interroga e
basta, non ti dice prima se il layer è queryable.

```bash
gdallocationinfo "WMS:<url GetMap del layer>" -wgs84 <lon> <lat>
```

## Scaricare vettoriale da un WFS — `ogr2ogr`

```bash
ogr2ogr -f GPKG out.gpkg "WFS:<endpoint>" <feature_type> \
  -spat <xmin> <ymin> <xmax> <ymax>   # ritaglio per bbox
```

## Altri servizi OGC

- **WCS** (coverage raster): `gdalinfo -json "WCS:<endpoint>"` → subdataset
  delle coverage; poi `gdal_translate "WCS:…"` per scaricare.
- **WMTS** (tile): `gdalinfo -json "WMTS:<endpoint>"` → subdataset per
  layer/tile-matrix-set.

In tutti i casi vale la stessa regola: GDAL elenca i layer/coverage ma **non**
porta i flag di capability — per dettagli (queryability, formati, stili) leggi
il GetCapabilities nativo.

## Esempio reale: catasto Agenzia delle Entrate

Servizio nazionale (copre tutta Italia, isole comprese). Scheda RNDT:
`openrndt get age:consultazione_catasto_wms`.

- **WMS**: `https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php`
  — 11 layer; gli edifici sono il layer **`fabbricati`** (titolo "Fabbricati"),
  NON `BU.Building`. Particelle = `CP.CadastralParcel`, mappe/zone =
  `CP.CadastralZoning`.
- **WFS**: `https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php`
  — solo 2 feature type: `CP:CadastralParcel` e `CP:CadastralZoning`. **I
  fabbricati NON sono nel WFS**: edifici disponibili solo come WMS (raster).
- **Interrogabili (GetFeatureInfo)**: solo `Cartografia_Catastale`,
  `CP.CadastralZoning`, `CP.CadastralParcel`. `fabbricati` **non** è queryable.
