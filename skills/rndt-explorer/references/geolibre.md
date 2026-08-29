# Vedere i dati trovati: dal record RNDT a una mappa GeoLibre

Il RNDT dice **dove** stanno i dati, non li mostra. Per guardarli senza aprire
QGIS si può usare [GeoLibre](https://geolibre.app), che apre progetti
`.geolibre.json` nell'app desktop, sul web e dentro Jupyter, e che ha una
propria skill e un proprio server MCP: la skill descrive i comandi, il server
MCP scrive e modifica i progetti (`create_project`, `add_ogc_layer`,
`add_vector_layer`, `add_geojson_layer`, `set_view`, `add_swipe`,
`export_html`).

Installazione e configurazione del server, una volta sola:

```bash
uv tool install "geolibre[mcp]"
claude mcp add -s local geolibre -- geolibre-mcp --root <cartella dei progetti>
```

Lo scope `local` (il default) limita il server all'utente e al progetto
corrente; `-s project` lo scrive in un `.mcp.json` condiviso. Il server scrive
solo dentro `--root`: i file dei progetti e i dati locali devono stare lì.

Questo riferimento raccoglie le regole verificate sul campo passando da record
RNDT reali a mappe che si vedono. Non sono dettagli di GeoLibre: sono i punti
dove il catalogo e un visualizzatore non combaciano.

## 1. Il nome del layer non è nel metadato

`add_ogc_layer` chiede `layers`, cioè il nome del layer dentro il servizio. Il
RNDT non lo fornisce: dà l'endpoint del server, dietro il quale possono esserci
decine di layer (il servizio uso del suolo dell'Emilia-Romagna ne ha sei, una
per annata, dietro un solo record di catalogo).

Due modi per ricavarlo:

- dal **GetCapabilities**, che è la fonte autorevole (vedi
  [`ogc-services.md`](./ogc-services.md));
- dal **primo link del metadato**, quando il portale è GeoNode: la forma
  `/layers/<workspace>:<layer>` contiene già il nome.

## 2. Promuovere l'endpoint a https

Il RNDT cataloga molti servizi in `http`. Le tile in `http` non arrivano
nemmeno a partire: la webview le blocca in pochi millisecondi, con `status 0` e
un messaggio generico su CORS o TLS che manda fuori strada. Prova lo stesso
endpoint in `https` prima di scrivere il progetto: molti server rispondono, e
alcuni fanno già 301 verso https.

## 3. Provare la risorsa con GDAL prima di aggiungerla

GeoLibre legge le risorse con GDAL, in-browser via duckdb-wasm. Lo stesso
`gdalinfo`/`ogrinfo` che gira in locale è quindi il controllo preventivo che
dice se la risorsa sarà leggibile, e vale per i servizi come per i file:

```bash
gdalinfo -json "WMS:<endpoint>" 2>/dev/null | jq …
ogrinfo -json -so "WFS:<endpoint>" 2>/dev/null | jq …
ogrinfo -json -so "/vsizip//vsicurl/<url dello zip>" 2>/dev/null | jq …
```

Restituisce in un colpo se la risorsa è raggiungibile, quanti oggetti ha, di
che geometria e in che CRS, più il nome del layer che serve al punto 1.

Un caso reale di cosa intercetta: uno shapefile zippato risponde 200 in https
con CORS `*` e in locale `ogrinfo /vsizip/file.zip` lo legge, ma da URL fallisce
perché il server risponde 200 all'intero file anche a una richiesta `Range`, e
`/vsizip//vsicurl/` ha bisogno delle range request per leggere l'indice
dell'archivio. In GeoLibre l'errore arriva come «GDAL Error (4): … does not
exist in the file system», che non dice nulla della causa; `ogrinfo` in locale
dice «Range downloading not supported by this server!».

Condizioni che una risorsa deve soddisfare per essere letta da URL nel browser:
schema `https`, header CORS, e - per gli archivi zip - supporto alle richieste
`Range` (`206` e `Accept-Ranges`).

## 4. Scrivere i bounds di ogni layer WMS

`wms_layer` non popola `source.bounds`: il layer arriva nel progetto senza
estensione dichiarata, e lo «zoom to fit» non ha su cosa inquadrare (non
succede nulla). L'estensione sta nel `BoundingBox CRS:84` del layer dentro il
GetCapabilities, e va copiata nel progetto come
`source.bounds = [west, south, east, north]`.

Attenzione: su un source raster MapLibre `bounds` limita anche le richieste di
tile, quindi un servizio che dichiara un'estensione più stretta del dato reale
fa sparire ciò che sta fuori. Meglio la bbox dichiarata per quel layer che
quella del record RNDT, che copre l'intero servizio.

## 5. Lo swipe fra due layer WMS

Per confrontare due annate dello stesso tema (uso del suolo 1853 contro 2011)
si usa `add_swipe`. Con i layer WMS, nelle versioni fino alla 2.8.0, ogni lato
va scritto con **due** identificatori: l'id del layer di progetto e l'id dello
style MapLibre `layer-<id>-raster`, entrambi sullo stesso lato. Con il solo id
del layer lo swipe mostra lo stesso layer su entrambe le metà
([PR #2155](https://github.com/opengeos/GeoLibre/pull/2155)).

## 6. Le risorse scaricabili vanno inlineate, non referenziate

Un file locale non si può referenziare per path: il lettore vive nel
filesystem virtuale della pagina e non vede il disco, quindi un progetto che
contiene un path locale si apre ma il layer resta vuoto (con path Linux e con
path Windows allo stesso modo). Le due strade che funzionano:

- **`add_vector_layer` con l'URL**, che legge sul posto qualunque vettoriale
  GDAL servito da URL (GeoParquet, FlatGeobuf, shapefile zippato, GeoJSON),
  purché la risorsa superi il controllo del punto 3. Nell'app desktop funziona;
  sul web lo shapefile zippato per URL al momento fallisce
  ([issue #2153](https://github.com/opengeos/GeoLibre/issues/2153));
- **`add_geojson_layer`**, che copia i dati dentro il progetto e quindi viaggia
  sempre: è la strada per una risorsa scaricata e convertita in locale.

## Cosa offre il catalogo, in numeri

Su un campione di 3000 record, i link a servizi e file scaricabili si
distribuiscono così:

| risorsa | occorrenze | come si aggiunge |
| --- | --- | --- |
| WMS | 2131 | `add_ogc_layer` |
| WFS | 1938 | `add_vector_layer` con `outputFormat=application/json` |
| shapefile zippato (`.zip`) | 917 | `add_vector_layer` per URL, o scaricato e inlineato |
| Esri MapServer | 159 | layer di tipo `arcgis` |
| GeoTIFF (`.tif`) | 30 | `add_raster_layer` solo se è un COG |
| WMTS | 18 | `add_ogc_layer` |
| WCS | 15 | unico modo per il raster come dato e non come immagine |
| ImageServer | 13 | layer di tipo `arcgis` |
| GeoPackage (`.gpkg`) | 12 | `add_vector_layer` |

## Citare la fonte nel progetto

Il campo `metadata` del progetto è libero: scriverci id del record, link alla
scheda, ente e servizio rende la mappa citabile e permette di risalire al dato.
Con i campi `url` e `org` degli output di `openrndt` viene gratis:

```json
"metadata": {
  "fonte": "Repertorio Nazionale dei Dati Territoriali (RNDT)",
  "record": "r_emiro:2016-04-01T154419",
  "scheda": "https://geodati.gov.it/geoportal-catalog/rest/metadata/item/r_emiro%3A2016-04-01T154419/html",
  "ente": "Regione Emilia-Romagna"
}
```

## Se l'app gira su Windows e i file stanno in WSL

L'app rifiuta i path UNC verso il filesystem WSL
(`\\wsl.localhost\...`: «not an absolute local project file path»), e non vede
i path Linux. Conviene tenere progetti e dati in una cartella Windows,
raggiungibile da WSL sotto `/mnt/c/...`, e puntare lì la `--root` del server
MCP.
