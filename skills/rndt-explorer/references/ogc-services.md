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

## Il GetCapabilities vivo non basta

Un server può rispondere 200 al GetCapabilities e non servire una sola mappa:
il WMS PCN della Carta Geologica d'Italia (`wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/Vettoriali/Carta_geologica.map`)
restituisce l'elenco dei layer e poi `ServiceException` a ogni GetMap, perché il
MapServer non raggiunge il proprio PostGIS. `openrndt resources` lo segna
`ok=true`, e ha ragione per quel che misura. Prima di scrivere «funzionante»,
chiedi una tile piccola e guarda il `Content-Type`:

```bash
# layer e bbox dal GetCapabilities, poi una GetMap 64x64
curl -s -o tile.png -w '%{http_code} %{content_type}\n' \
  "<endpoint>?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=<layer>&STYLES=&CRS=EPSG:4326&BBOX=36,6,48,19&WIDTH=64&HEIGHT=64&FORMAT=image/png"
# 200 image/png → vivo.  200 text/xml o application/vnd.ogc.se_xml → leggi tile.png: è l'eccezione.
```

**Una tile vuota non è un servizio morto: spesso è una scala sbagliata.** I layer
possono dichiarare `MinScaleDenominator`/`MaxScaleDenominator`, e fuori da quella
finestra il server risponde `200 image/png` con un PNG interamente trasparente,
senza errori. Prima di scartare un layer leggi i suoi limiti, e leggi quelli del
layer che intendi usare: in un GetCapabilities con più layer è facile prendere i
valori del vicino e scartare per errore proprio quello giusto (successo in un test
sul 1:100.000 di ISPRA, scartato citando la scala di un altro layer, mentre a
richiesta rifatta disegnava).

```bash
# limiti di scala per layer, in ordine di dichiarazione
xmllint --format caps.xml | grep -E "<(Name|Title|MinScaleDenominator|MaxScaleDenominator)>"

# e poi guarda la tile: 200 image/png non basta, contale i colori
python3 -c "from PIL import Image; im=Image.open('tile.png'); print(im.size, len(im.getcolors(1<<20) or []))"
# 1 colore solo = vuota (fuori scala, o stile che non copre l'area): cambia scala o bbox prima di concludere
```

Per un WFS l'equivalente è `GetFeature` con `count=1`. Due trappole in più,
viste sugli ISPRA: alcuni GeoServer servono i layer con lo **stile di default**
(poligoni grigi) e la carta non si legge senza il raster affiancato; e un server
con TLS legacy (`sgi2.isprambiente.it`, solo TLS 1.2 `AES128-SHA`) risponde a
curl ma dava `ConnectError` a httpx fino alla CLI 3.1.0.

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
- **CRS del WMS**: solo `EPSG:6706`, `EPSG:4258` e le UTM (25832-25834,
  3044-3046). Una GetMap in `EPSG:3857` o `EPSG:4326` risponde 200 con un
  `ServiceExceptionReport` XML; in `EPSG:6706` (bbox in gradi, lon,lat con WMS
  1.1.1) restituisce il PNG. Nessuna intestazione CORS: niente uso in
  applicazioni web (vedi `geolibre.md`).

### Il WFS catastale rifiuta alcune richieste: ripeti con un parametro innocuo

Una parte delle GetFeature (circa una su dieci in un campione del 2026-09-22)
risponde **HTTP 200** con:

```xml
<ServiceExceptionReport version="1.1.1"><ServiceException code="InvalidFormat"><![CDATA[Richiesta non valida ]]></ServiceException></ServiceExceptionReport>
```

L'esito dipende dalla stringa esatta della richiesta ed è sempre lo stesso per
la stessa stringa: non da `MAXFEATURES`, dal feature type o dalla versione
(fallisce sia in 1.1.0 sia in 2.0.0). Cambiare un carattere qualsiasi lo fa
sparire, e il modo pulito è ripetere con un parametro in più (`&_=1`, poi
`&_=2`). Riconosci l'errore dal corpo, non dallo status.

```bash
W='https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php'
Q='service=WFS&version=2.0.0&request=GetFeature&typeNames=CP:CadastralZoning&bbox=38.1288,14.8336,38.1438,14.8536,urn:ogc:def:crs:EPSG::6706'
for k in "" "&_=1" "&_=2"; do
  curl -s "$W?$Q$k" -o zone.gml
  grep -q ServiceExceptionReport zone.gml || break
  sleep 5
done
```

Buone pratiche per questo servizio: WFS 2.0.0 con il CRS come URN in coda al
bbox (ordine lat,lon), bbox di pochi km² e aree grandi divise in tile, qualche
secondo di pausa fra le chiamate, niente `MAXFEATURES`.
