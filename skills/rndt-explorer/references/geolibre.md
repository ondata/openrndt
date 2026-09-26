# Guida: visualizzare i risultati di openrndt con GeoLibre

Il RNDT dice **dove** stanno i dati, non li mostra. [GeoLibre](https://geolibre.app)
apre progetti `.geolibre` nell'app desktop, sul web e dentro Jupyter, e ha
una propria skill e un proprio server MCP: la skill descrive i comandi, il
server MCP scrive i progetti (`create_project`, `add_ogc_layer`,
`add_vector_layer`, `add_geojson_layer`, `classify_layer`, `add_legend`,
`set_view`, `add_swipe`, `export_html`).

Questa guida è il ponte fra le due cose: cosa si può mettere su mappa partendo
da una ricerca, in che ordine, e cosa controllare prima per non ritrovarsi una
mappa bianca. Tutto quello che segue è stato provato su record reali.

## Prima di iniziare

```bash
uv tool install "geolibre[mcp]"
claude mcp add -s local geolibre -- geolibre-mcp --root <cartella dei progetti>
```

Il parametro `crs` di `add_ogc_layer` (WMS senza `EPSG:3857`, punto B.4)
richiede `geolibre` 3.1.0 e GeoLibre Desktop 3.1.0. Dopo l'aggiornamento
(`uv tool install "geolibre[mcp]" --reinstall`) il server MCP va riavviato:
quello già in esecuzione non vede i parametri nuovi.

Lo scope `local` (default) limita il server all'utente e al progetto corrente;
`-s project` lo scrive in un `.mcp.json` condiviso. Il server legge e scrive
**solo dentro `--root`**: progetti e dati locali devono stare lì, altrimenti
ogni chiamata risponde «outside this server's workspace».

Se l'app gira su Windows e i file stanno in WSL, la `--root` va su una cartella
Windows (`/mnt/c/Users/<utente>/maps` da WSL, `C:\Users\<utente>\maps` per
l'app): l'app non vede i path Linux e rifiuta i path UNC `\\wsl.localhost\...`
con «not an absolute local project file path».

## Tre cose diverse da mettere su mappa

Prima di scrivere un progetto, decidi quale delle tre stai facendo: cambiano
comandi, tempi e limiti.

| Cosa | Da dove | Comando GeoLibre |
| --- | --- | --- |
| **Dove stanno i dataset** trovati da una ricerca | `openrndt footprints` | `add_geojson_layer` |
| **Il dato visto attraverso un servizio** (nessun download) | link `WMS`/`WMTS` del record | `add_ogc_layer` |
| **Il dato vero**, da servizio scaricabile o da file | link `WFS` o URL di un file | `add_vector_layer` (per URL) o `add_geojson_layer` (inline) |

---

## A. La mappa dei risultati di ricerca

È il modo più rapido per capire *dove* è coperto un tema e quali record hanno
davvero qualcosa di scaricabile. `footprints` restituisce una
`FeatureCollection` con la bbox di ogni metadato e le proprietà `id`, `title`,
`org`, `type`, `updated`, `indexed`, `open`, `license`, `url`, `resources`.

```bash
openrndt footprints --q "uso del suolo" --num 40 > footprints.geojson
```

Poi `add_geojson_layer` sul file. Accetta gli stessi filtri di `search`, quindi
la mappa può essere quella di una ricerca già raffinata. Prima di aggiungerlo
togli i bbox mondiali: bastano tre schede sbagliate per coprire la mappa e
rendere inutile lo zoom del layer - vedi «Il bbox sbagliato nella scheda».

Per **colorare per un attributo**, `classify_layer` vuole una colonna
**numerica**: `resources` è un array e `open` un booleano, quindi vanno
derivati prima con `jq`.

```bash
jq '{type, features: [.features[]
      | .properties += {n_risorse: (.properties.resources|length),
                        open_flag: (if .properties.open then 1 else 0 end)}
      | del(.properties.resources)]}' footprints.geojson > footprints-arricchito.geojson
```

Su questo `classify_layer` con `column: "n_risorse"` separa a colpo d'occhio i
metadati con risorse collegate da quelli senza - su 40 record "uso del suolo"
solo 8 ne avevano. Un `add_legend` con `legend_dict` rende la mappa leggibile a
chi non ha fatto la ricerca.

---

## B. Il dato via WMS

Il percorso più corto: nessun download, il server disegna.

1. **Prendi l'endpoint** dal record:

   ```bash
   openrndt --format json search --q "uso del suolo" --num 50 \
     | jq -r '.results[].links[]? | select(.dctype=="WMS") | .href' | sort -u
   ```

2. **Ricava il nome del layer**, che nel metadato non c'è. Il RNDT dà
   l'endpoint del server, dietro il quale possono esserci decine di layer: il
   servizio uso del suolo dell'Emilia-Romagna ne ha sei, una per annata, dietro
   un solo record. Due modi: il **GetCapabilities**, che è la fonte autorevole
   (vedi [`ogc-services.md`](./ogc-services.md)), oppure il **primo link del
   metadato** quando il portale è GeoNode, nella forma
   `/layers/<workspace>:<layer>`.

3. **Promuovi l'endpoint a `https`.** Il RNDT cataloga molti servizi in `http`,
   e le tile in `http` non arrivano nemmeno a partire: la webview le blocca in
   pochi millisecondi, con `status 0` e un messaggio generico su CORS o TLS che
   manda fuori strada. Molti server rispondono in https, alcuni fanno già 301.

4. **Controlla il CRS prima di aggiungere il layer.** MapLibre disegna in Web
   Mercator: se il layer espone `EPSG:3857` nel GetCapabilities va bene così.
   Se non lo espone, di solito il server risponde 200 con un
   `ServiceExceptionReport` in XML e il layer resta vuoto senza errori (alcuni
   server lo accettano lo stesso, per esempio ArcGIS di ISPRA: una GetMap a mano
   in `EPSG:3857` lo dice). Da GeoLibre 3.1.0 (app desktop e
   pacchetto `geolibre[mcp]`) lo si vede lo stesso, ma solo nella desktop, che
   riproietta: passa ad `add_ogc_layer` `crs` con un CRS che sia insieme
   esposto dal layer e fra quelli che GeoLibre sa riproiettare, cioè i
   geografici `EPSG:4326`, `EPSG:4258`, `EPSG:6706`, `CRS:84`. Se il layer
   espone solo CRS proiettati (UTM, Gauss-Boaga o altri) non c'è un CRS in
   comune e il layer non si vede: `add_ogc_layer` rifiuta quei valori con un
   `ValueError`. Nel campione del catalogo RNDT misurato il 2026-09-26 (un
   endpoint per host, 54 risposte) i 14 server senza `EPSG:3857` esponevano
   tutti anche un CRS geografico.

   ```bash
   curl -s "<endpoint>?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities" \
     | grep -o '<CRS>[^<]*</CRS>' | sort -u
   ```

   Web ed `export_html` restano limitati a `EPSG:3857` e vogliono anche
   l'intestazione CORS (vedi più sotto); nella desktop dalla 2.9.0 le tile WMS
   passano per via nativa. L'Add Data dell'app scrive sempre `EPSG:3857`: il
   `crs` si imposta solo nel progetto (MCP, libreria Python o a mano).

5. **`add_ogc_layer`** con `bounds`, l'estensione del layer: senza, lo «zoom
   to fit» non ha su cosa inquadrare (non succede nulla). Il valore sta nel
   `BoundingBox CRS:84` di quel layer nel GetCapabilities, nell'ordine
   `[west, south, east, north]`. Con versioni precedenti di `geolibre` che non
   accettano `bounds`, va aggiunto a mano come `source.bounds` sul layer.

   Attenzione: su un source raster `bounds` limita anche le richieste di tile,
   quindi un servizio che dichiara un'estensione più stretta del dato reale fa
   sparire ciò che sta fuori. Meglio la bbox del singolo layer che quella del
   record, che copre l'intero servizio.

**Confrontare due annate** con `add_swipe`: nelle versioni fino alla 2.8.0 ogni
lato va scritto con **due** identificatori, l'id del layer di progetto e l'id
dello style MapLibre `layer-<id>-raster`, entrambi sullo stesso lato. Con il
solo id del layer lo swipe mostra lo stesso layer su entrambe le metà
([PR #2155](https://github.com/opengeos/GeoLibre/pull/2155)).

---

## C. Il dato scaricabile

### WFS: il dato vettoriale senza scaricarlo

È il secondo tipo di risorsa più diffuso nel catalogo e il più comodo dopo il
WMS, perché una `GetFeature` con `outputFormat=application/json` **è** un URL
GeoJSON, quindi si passa a `add_vector_layer` così com'è.

```bash
# 1. i feature type del servizio (il metadato non li elenca)
ogrinfo "WFS:<endpoint>" 2>/dev/null | grep -E "^[0-9]+:"

# 2. l'URL da dare a GeoLibre
<endpoint>?service=WFS&version=2.0.0&request=GetFeature\
&typeNames=<feature type>&count=1000\
&outputFormat=application/json&srsName=EPSG:4326
```

**`srsName=EPSG:4326` non è opzionale.** Senza, GeoServer risponde nel CRS
nativo del dato: su un servizio regionale ho ottenuto coordinate come
`[555955, 4377948]` (EPSG:7791) invece di `[9.65, 39.55]`, e in una mappa web
finiscono fuori dal mondo. E `count` va sempre messo: senza limite un feature
type grosso scarica tutto dentro il browser.

### File scaricabili

`add_vector_layer` legge da URL qualunque vettoriale che GDAL sappia aprire -
GeoParquet, FlatGeobuf, GeoJSON, GeoPackage, shapefile zippato - senza
scaricare né convertire nulla: i dati restano alla fonte e il progetto pesa
pochi kilobyte. Ma la risorsa deve reggere le condizioni del browser.

**Fai sempre il pre-check con GDAL.** GeoLibre legge con GDAL (in-browser, via
duckdb-wasm), quindi lo stesso comando che gira in locale predice cosa farà la
pagina, e vale per i file come per i servizi:

```bash
ogrinfo -json -so "/vsizip//vsicurl/<url dello zip>" 2>/dev/null | jq …
ogrinfo -json -so "WFS:<endpoint>" 2>/dev/null | jq …
gdalinfo -json "WMS:<endpoint>" 2>/dev/null | jq …
```

Restituisce in un colpo se la risorsa è raggiungibile, quanti oggetti ha, di
che geometria e in che CRS - più il nome del layer che serve al punto B.2.

Le tre condizioni che ho visto fallire, in ordine di frequenza: schema `http`,
header CORS assenti, e - per gli archivi zip - nessun supporto alle richieste
`Range`. L'ultima è la più insidiosa: un server può rispondere 200 in https con
CORS `*` e sembrare a posto, ma se risponde 200 anche a `Range: bytes=0-99`
(invece di `206` con `Accept-Ranges`), `/vsizip/` non riesce a leggere l'indice
dell'archivio. In GeoLibre l'errore arriva come «GDAL Error (4): … does not
exist in the file system», che non dice nulla della causa; `ogrinfo` in locale
dice «Range downloading not supported by this server!».

**Quando il pre-check fallisce**, la risorsa va scaricata e **inlineata** con
`add_geojson_layer`, che copia i dati dentro il progetto. Non referenziarla per
path: il lettore vive nel filesystem virtuale della pagina e non vede il disco,
quindi un progetto con un path locale si apre ma il layer resta vuoto, con path
Linux e con path Windows allo stesso modo.

Nota nota: lo shapefile zippato letto da URL funziona nell'app desktop e al
momento fallisce sul web ([issue #2153](https://github.com/opengeos/GeoLibre/issues/2153)).

---

## D. Altri usi che hanno senso

### Una mappa di più servizi dello stesso tema

Il catalogo è fatto di pezzi regionali: un tema nazionale si vede solo mettendo
insieme i WMS di più enti sulla stessa mappa. La ricerca dà gli endpoint, e
ogni `add_ogc_layer` aggiunge una tessera - ognuna con i suoi `bounds`, così lo
«zoom to fit» su un layer porta sulla sua regione.

### Una mappa di qualità: quali risorse rispondono davvero

`openrndt resources` fa un health check degli endpoint di un record, e il suo
esito si può riportare sui footprint per vedere *dove* il catalogo è vivo e
dove no. Attenzione a quotare gli id, che contengono `:`.

```bash
openrndt footprints --q "uso del suolo" --num 40 > footprints.geojson
IDS=$(jq -r '.features[].properties.id' footprints.geojson | head -8)
eval openrndt --format json resources $(printf '"%s" ' $IDS) > resources.json

jq --slurpfile r resources.json '
  ($r[0].results | map({key: .id, value: ([.resources[]? | select(.ok==true)] | length)}) | from_entries) as $ok
  | {type, features: [.features[]
      | select($ok[.properties.id] != null)
      | .properties = (.properties + {n_ok: $ok[.properties.id]} | del(.resources))]}' \
  footprints.geojson > qualita.geojson
```

Poi `add_geojson_layer` e `classify_layer` su `n_ok`. Su un campione di otto
record "uso del suolo" (2026-08-29), sette non avevano alcuna risorsa collegata
e l'ottavo ne aveva una viva su due (il 30 agosto erano già due i record con
`n_ok=1`: è una fotografia, non una regola): è il tipo di cosa che una tabella non fa vedere e una
mappa sì.

### Tipi di risorsa che non ho verificato

Per onestà, questi restano da provare: **WMTS** (`add_ogc_layer`, variante del
percorso WMS), **WCS** (l'unico modo per avere il raster come dato e non come
immagine), **GeoTIFF** (`add_raster_layer`, ma solo se è un COG: altrimenti
serve un `gdal_translate` e non è più un percorso "live"), ed **Esri
MapServer/ImageServer**. Su questi ultimi il campione è concentrato su pochi
host e quelli che ho provato non rispondevano - host che non risolve o timeout
- quindi non ho potuto verificare nulla: prima di scrivere un progetto, fai il
pre-check.

## Quando qualcosa non si vede

| Sintomo | Causa probabile | Come verificarlo |
| --- | --- | --- |
| Layer nell'elenco, mappa vuota, tile fallite in 0-4 ms | endpoint in `http` | riprova l'URL in `https` |
| `AJAXError: Failed to fetch (0)` sulla tile, ma `curl` sullo stesso URL dà 200 `image/png` | CORS: manca `Access-Control-Allow-Origin`, oppure il server ne manda **due** (ArcGIS ISPRA: uno riflesso e uno `*`), valore che i browser rifiutano | `curl -sI -H "Origin: https://geolibre.app" "<tile url>" \| grep -i access-control`: deve esserci **una** riga. Non è risolvibile lato GeoLibre: MapLibre usa `fetch`. Una pagina Leaflet (`<img>`) mostra la stessa tile |
| Layer WMS vuoto, nessun errore, la GetMap a mano in `EPSG:3857` dà un `ServiceExceptionReport` | il layer non espone `EPSG:3857` | CRS del GetCapabilities, poi `crs` geografico in `add_ogc_layer` (punto B.4, solo desktop) |
| GetCapabilities 200 ma nessuna tile arriva, o arriva un XML | il server serve il capabilities ma non le mappe (PCN: `ServiceException`, database non raggiungibile) | una GetMap a mano: `Content-Type` deve essere `image/*` (vedi `ogc-services.md`) |
| Layer nell'elenco, mappa vuota, nessuna richiesta | risorsa non leggibile | `ogrinfo` sullo stesso path che usa GeoLibre |
| «GDAL Error (4): does not exist in the file system» | zip remoto senza `Range`, o path locale | `curl -I -H "Range: bytes=0-99"`: deve dare `206` |
| Lo «zoom to fit» funziona solo sui layer GeoJSON | i layer WMS/WMTS nascono senza `source.bounds` | `jq -r '.layers[] \| "\(.name)\t\(.source.bounds // "-")"' progetto.geolibre` - vedi «Dare un'estensione ai layer WMS» |
| Lo swipe mostra lo stesso layer sui due lati | manca lo style id nei lati | vedi la nota su `add_swipe` |
| Dati fuori posto o invisibili a scala giusta | CRS non geografico | il `coordinateSystem` che riporta `ogrinfo` |
| Un poligono del footprint copre il mondo, lo zoom del layer inquadra il pianeta | la scheda ISO dichiara `-180/-90/180/90` | `openrndt get <id> --xml \| grep -A8 EX_GeographicBoundingBox` - vedi «Il bbox sbagliato nella scheda» |

## Dare un'estensione ai layer WMS

`add_ogc_layer` scrive endpoint, layer e formato, non l'estensione: nel progetto
quei layer restano senza `source.bounds`. GeoLibre calcola l'estensione dalle
feature solo per i layer GeoJSON inline, quindi lo «zoom to fit» funziona sul
footprint e non fa nulla su un WMS - e chi apre il progetto non ha modo di
raggiungere un layer regionale partendo dalla vista nazionale.

Il bbox va scritto a mano. Due fonti, in quest'ordine:

- il metadato RNDT: `openrndt --format json get <id> | jq -c .bbox` dà
  `{"xmin":…,"ymin":…,"xmax":…,"ymax":…}`, già in WGS84;
- il GetCapabilities del servizio, quando il record non ha bbox o l'ha
  nazionale mentre il layer è locale.

Dal GetCapabilities prendi **`EX_GeographicBoundingBox`**, non `<BoundingBox
CRS="EPSG:4326">`: in WMS 1.3.0 l'EPSG:4326 ha l'asse invertito e diversi
server ci scrivono dentro numeri già scambiati (Valle d'Aosta:
`minx="45.465446"` su un `minx` che dovrebbe essere una longitudine).
`EX_GeographicBoundingBox` è sempre lon/lat e non ha questo problema.

```bash
curl -s "<endpoint>?service=WMS&request=GetCapabilities&version=1.3.0" \
  | grep -A4 EX_GeographicBoundingBox | head -5
```

Poi scrivilo nel progetto, come `[minlon, minlat, maxlon, maxlat]`:

```bash
jq '.layers |= map(if .name == "Sardegna - aree percorse dal fuoco 2021"
      then .source.bounds = [8.14, 38.85, 9.83, 41.31] else . end)' \
   progetto.geolibre > tmp && mv tmp progetto.geolibre
```

Con più layer conviene un file `nome -> bbox` e un solo passaggio:

```bash
jq --slurpfile b bounds.json \
   '.layers |= map(if ($b[0][.name]) then .source.bounds = $b[0][.name] else . end)' \
   progetto.geolibre > tmp && mv tmp progetto.geolibre
```

GeoLibre legge `source.bounds` e ricade su `metadata.bounds` se il primo non è
valido, quindi puoi anche tenere il bbox nel blocco `metadata` insieme a record
e permalink RNDT. Rigenera l'HTML dopo: `export_html` fotografa il progetto al
momento della chiamata.

## Il bbox sbagliato nella scheda

Un footprint può contenere poligoni che coprono il mondo intero: la scheda ISO
dichiara `-180/-90/180/90`. Non è un difetto di `footprints`, che riporta quello
che c'è: la sorgente XML ha davvero quei numeri, e lo verifichi con

```bash
openrndt get <id> --xml | grep -A8 EX_GeographicBoundingBox
```

Sono pochi ma costosi: coprono la mappa, e lo «zoom to fit» del layer inquadra
il pianeta invece dell'Italia. Sui 277 record di una ricerca su «incendi» ce ne
sono 3, tutti della Provincia autonoma di Trento (Servizio Foreste e fauna,
Servizio Geologico).

Non buttarli: separali in un layer proprio, spento, così restano documentati e
lo zoom del layer principale torna utile.

```bash
jq '{type:"FeatureCollection",features:[.features[]
      | (((.geometry.coordinates[0]|map(.[0])|max) - (.geometry.coordinates[0]|map(.[0])|min))) as $w
      | .properties.estensione = (if $w > 300 then "mondiale (bbox errata)"
          elif $w > 10 then "nazionale" elif $w > 2 then "regionale" else "locale" end)]}' \
   footprints.geojson > fp_cls.geojson

jq '{type:"FeatureCollection",features:[.features[]|select(.properties.estensione != "mondiale (bbox errata)")]}' fp_cls.geojson > fp_ok.geojson
jq '{type:"FeatureCollection",features:[.features[]|select(.properties.estensione == "mondiale (bbox errata)")]}' fp_cls.geojson > fp_mondo.geojson
```

La soglia `> 300` gradi isola solo il bbox mondiale ed è diversa da quelle di
[`workflows.md`](./workflows.md) §10, che separano locale, regionale e
nazionale: quelle scremano il rumore di una ricerca, questa toglie un errore di
compilazione. L'attributo `estensione` che resta sulle feature serve poi a
`classify_layer` o a un filtro nell'app.

## Citare la fonte

Il campo `metadata` del progetto è libero: scriverci id del record, link alla
scheda, ente e servizio rende la mappa citabile e permette a chi la riceve di
risalire al dato. Con i campi `url` e `org` degli output di `openrndt` viene
gratis:

```json
"metadata": {
  "fonte": "Repertorio Nazionale dei Dati Territoriali (RNDT)",
  "record": "r_emiro:2016-04-01T154419",
  "scheda": "https://geodati.gov.it/geoportal-catalog/rest/metadata/item/r_emiro%3A2016-04-01T154419/html",
  "ente": "Regione Emilia-Romagna"
}
```

## Tre consegne, scelte dal destinatario

Alla fine del lavoro hai tre oggetti possibili, e non sono intercambiabili:

- **il file progetto** (`.geolibre`: dalla
  [v2.9.0](https://github.com/opengeos/GeoLibre/releases/tag/v2.9.0) è
  l'estensione nativa, registrata nel sistema - doppio clic e si apre nell'app.
  `.geolibre.json` resta letto, ma non è più la forma da consegnare). È la
  fonte: pochi KB di JSON leggibile con endpoint, layer, bounds e il blocco
  `metadata` con record e permalink RNDT. Chi lo riceve può cambiare stile,
  aggiungere un layer, spostare la vista. Va a chi ha GeoLibre Desktop o lo può
  installare, e va comunque conservato accanto a qualunque altra consegna.
- **la pagina HTML** di `export_html`: non è una figura, è l'applicazione dentro
  una pagina. Chi la riceve apre un GIS senza installare nulla e può continuare il
  lavoro: aggiungere un proprio layer, confrontare due annate con lo swipe,
  interrogare gli attributi, cambiare stile, esportare. L'interfaccia di editing
  che resta a vista è il prezzo di questo, non un difetto: una pagina scritta a
  mano con Leaflet è più pulita e mostra anche i WMS senza CORS, ma fa solo quello
  che hai deciso tu, e chi la riceve non può verificarci nulla. Scegli Leaflet
  quando conta la resa o quando il servizio non manda CORS, `export_html` quando
  vuoi che l'altro possa lavorarci.

- **un URL a un file che pubblichi tu**, senza allegati: metti il progetto o il
  `footprints.geojson` su un host che permette CORS (gist, GitHub Pages, un bucket)
  e mandi `https://web.geolibre.app/?url=<progetto>` o `?data=<geojson>`. Il dato lo
  scarica il browser di chi guarda; nessun server in mezzo. Il CORS del file lo
  controlli tu, quello dei layer (WMS, WFS) no: vale lo stesso pre-check delle
  altre due. Vedi «Condividere con un URL».

Regola: consegna il progetto quando il destinatario ha l'app, l'HTML quando non
ce l'ha, l'URL quando vuoi un link e non un allegato; e tieni sempre il progetto.

Il vincolo comune alle tre: i layer li scarica il browser di chi guarda, in
MapLibre, con `fetch`. La pagina HTML non «contiene» i dati e aprirla da un file
locale non aiuta (origine `null`): un WMS o un WFS che non manda
`Access-Control-Allow-Origin` non si vede né nell'HTML né via URL. Il pre-check
CORS non è un dettaglio della consegna 3, è la condizione di tutte.

**Salva come `.geolibre`.** I tool di `geolibre-mcp` che *scrivono la struttura*
del progetto rifiutano ancora quell'estensione (`expected a file ending in .json
or .geolibre.json`): `create_project` e `remove_layer` di sicuro. Chi legge o
aggiunge - `add_*_layer`, `update_layer`, `set_view`, `describe_project`,
`export_html` - accetta il path già rinominato. Quindi: crea con
`.geolibre.json`, rinomina quando hai finito, e se poi devi rimuovere un layer
rinomina indietro per quella chiamata.

```bash
mv progetto.geolibre.json progetto.geolibre
```

**Nella desktop il vincolo vale a metà** (misurato il 2026-08-30 con un progetto
di cinque layer, file `test-cors-desktop.geolibre.json`, su una versione
precedente alla 2.9.0: dalla 2.9.0 la desktop scarica anche le tile WMS per via
nativa, [PR #2169](https://github.com/opengeos/GeoLibre/pull/2169), e le righe
WMS senza CORS della tabella sono da rimisurare):

| Layer | CORS del server | Web / HTML | Desktop |
| --- | --- | --- | --- |
| WFS Sardegna, GeoJSON via `add_vector_layer` | un header `*` | si vede | si vede |
| WFS FVG, GeoJSON via `add_vector_layer` | nessun header | **non** si vede | **si vede** |
| WMS ISPRA GeoServer 1:500K | un header `*` | si vede | si vede |
| WMS FVG | nessun header (tile 200 a curl) | non si vede | **non** si vede |
| WMS ISPRA ArcGIS 1:1M | **due** header | non si vede | non si vede |

Cioè: i **dati vettoriali da URL** la desktop li legge per via nativa, fuori
dalla webview, e CORS non conta (come in QGIS); le **tile WMS** le chiede ancora
MapLibre dentro la webview, con le regole del browser. Il progetto aperto
nell'app è quindi la consegna più robusta per WFS e GeoJSON, ma per un WMS senza
CORS non serve: lì l'alternativa è una pagina Leaflet, che carica le tile come
`<img>`, oppure QGIS.

## Condividere con un URL

Provato il 2026-08-30 su GeoLibre Web (doc: [Embedding & Sharing](https://geolibre.app/user-guide/embedding/)).

Due forme:

```text
https://web.geolibre.app/?data=<URL del dato>          # GeoJSON, GeoParquet, PMTiles, COG, ZIP di GeoJSON, endpoint REST che risponde FeatureCollection
https://web.geolibre.app/?url=<URL del .geolibre>       # un progetto pubblico: vista, layer e stile sono i suoi
```

`data` si ripete per più dataset; `layout=viewer` o `maponly` tolgono l'interfaccia
di authoring per chi deve solo guardare. Il valore di `data` va percent-encoded
se contiene `&` (ogni `GetFeature` lo contiene): senza, `&VERSION=` diventa un
parametro di GeoLibre. Da shell: `jq -sRr @uri`.

Cosa entra da RNDT, in ordine di affidabilità:

- **un progetto**: lo stesso `.geolibre` della consegna 1, messo su un URL
  pubblico e aperto con `?url=`. La vista è quella salvata. È il caso buono: il
  file lo ospiti tu.
- **un `footprints.geojson` pubblicato** (gist, bucket, pagina del progetto). Non
  c'è un parametro di vista: la mappa si adatta all'estensione dei dati, quindi con
  le bbox nazionali e mondiali dentro si vede il pianeta. Togliile prima con la
  ricetta di `workflows.md` §10 (su «uso del suolo» in Sicilia: da 82 a 7 feature).
- **la `GetFeature` di un WFS di un ente**, con `OUTPUTFORMAT=application/json` e
  `SRSNAME=EPSG:4326`: in teoria «un endpoint che risponde con una
  FeatureCollection», in pratica un caso marginale. Misurato il 2026-08-30 su 3000
  record `dataset`: 163 endpoint WFS distinti per 2041 link; 98 rispondono al
  GetCapabilities 2.0.0, 70 dichiarano GeoJSON, **48 mandano anche CORS**, cioè 236
  link su 2041 (11,6%). L'Agenzia delle Entrate vale da sola 1437 link e non emette
  GeoJSON; tolta lei si sale al 39%, ma quasi tutto è Regione Sardegna e Provincia
  di Bolzano (`civis.bz.it`). FVG parla GeoJSON su molti GeoServer e non manda CORS
  su nessuno; Veneto e ARPAV rispondono 301 verso `https` (non seguiti dalla sonda).
  Non presentarlo come percorso generale: tentalo solo dopo il pre-check, e se
  fallisce scarica il GeoJSON e pubblicalo tu.

Pre-check obbligatorio, prima di mandare il link:

```bash
curl -sI -H "Origin: https://web.geolibre.app" "<url del dato>" | grep -i "^HTTP\|access-control-allow-origin"
# serve 200 e UNA riga Access-Control-Allow-Origin (* o l'origin). Zero righe = non si apre. Due righe = non si apre (ArcGIS ISPRA).
```

Un gist raw di GitHub manda `*`; i GeoServer regionali a volte sì (Sardegna,
Bolzano) a volte no (FVG). Un raw di gist senza hash resta in cache qualche minuto dopo un aggiornamento:
per il link usa il `raw_url` con il commit (`gh api gists/<id>`).


Su un campione di 3000 record:

| risorsa | occorrenze | come si aggiunge |
| --- | --- | --- |
| WMS | 2131 | `add_ogc_layer` |
| WFS | 1938 | `add_vector_layer` con `outputFormat=application/json` |
| shapefile zippato (`.zip`) | 917 | `add_vector_layer` per URL, o scaricato e inlineato |
| Esri MapServer | 159 | layer di tipo `arcgis` |
| GeoTIFF (`.tif`) | 30 | `add_raster_layer`, solo se è un COG |
| WMTS | 18 | `add_ogc_layer` |
| WCS | 15 | unico modo per il raster come dato e non come immagine |
| ImageServer | 13 | layer di tipo `arcgis` |
| GeoPackage (`.gpkg`) | 12 | `add_vector_layer` |

Il WMS resta il percorso più affidabile, ed è anche il più diffuso: se il
record ne ha uno, parti da lì.
