# Il catalogo RNDT via CSW (per flussi GDAL/OGR e QGIS)

Oltre all'API REST, il RNDT espone un **servizio CSW** (OGC Catalogue Service for the Web 2.0.2) su `https://geodati.gov.it/RNDT/csw`.

**Quando usarlo — risposta breve: quasi mai.** Come sorgente dati non offre nulla che l'API REST non dia già, e su filtri e ordinamento è nettamente inferiore. Ha senso in un caso solo: quando sei dentro un flusso **GDAL/OGR o QGIS**, dove il CSW è consumabile da strumenti che l'API REST proprietaria non sanno parlare.

Tutto ciò che segue è verificato live (2026-07-17, riconfermato 2026-08-30) con GDAL 3.11 e 3.13.

## Cosa NON guadagni passando al CSW

| | CSW | REST | Vantaggio CSW |
|---|---|---|---|
| Ricerca full-text "incendi" | `anytext LIKE '%incendi%'` → 190 | `q=incendi` → 190 | nessuno |
| Metadato ISO 19139 completo | `GetRecordById` | `rest/metadata/item/{id}/xml` | nessuno: file **byte-identici** (stesso MD5) |
| Ordinamento | `SortBy` **ignorato** | `sort=apiso_Modified_dt:desc` funziona | il REST è meglio |
| Filtro per data | **impossibile** (vedi sotto) | `q=apiso_PublicationDate_dt:[…]` funziona | il REST è meglio |
| Filtro per categoria/ente | i queryables `apiso:*` non funzionano | `q=keywords_s:…`, `q=contact_organizations_s:…` | il REST è meglio |
| Filtro spaziale | `-spat` → **30** record (area Palermo) | `--bbox` → **748** sulla stessa area | il REST è meglio |

Il vantaggio reale è uno solo, ed è di **forma, non di potenza**: il catalogo diventa un **layer vettoriale** con geometria bounding box, quindi apribile in QGIS ed esportabile con `ogr2ogr` come qualunque altro dato. Non ottieni informazioni in più: ottieni le stesse in un contenitore che gli strumenti GIS sanno aprire.

## Il layer

Il driver espone **un solo layer**, chiamato `records`:

```bash
ogrinfo -ro "CSW:https://geodati.gov.it/RNDT/csw"
# 1: records (Polygon)
```

Schema (23.632 feature, geometria `boundingbox` in EPSG:4326):

```bash
ogrinfo -ro -so "CSW:https://geodati.gov.it/RNDT/csw" records
```

Campi disponibili: `identifier`, `other_identifiers`, `title`, `type`, `subject`, `other_subjects`, `references`, `other_references`, `modified`, `abstract`, `date`, `language`, `rights`, `format`, `other_formats`, `creator`, `source`, `anytext`.

> ⚠️ **Tre campi ingannano** (verificato):
> - `rights` (licenza) è **sempre vuoto**: per la licenza usa il REST e guarda `isOpendata`, `apiso_AccessConstraints_s` **e** `apiso_OtherConstraints_s`.
> - `creator` contiene lo **username interno** di chi ha caricato la scheda (es. `massimiliano.molinari`), non l'ente responsabile. Per l'ente usa il REST (`contact_organizations_s`, `EnteResponsabile_s`).
> - `modified` è la data di **reindicizzazione del catalogo** (tutti i record collassano sullo stesso timestamp), non la data del metadato. Per quella usa `apiso_Modified_dt` via REST.

## Ricerca per testo

`-where` viene tradotto dal driver in `PropertyIsLike`. Il campo da usare è `anytext`:

```bash
ogrinfo -ro "CSW:https://geodati.gov.it/RNDT/csw" records \
  -where "anytext LIKE '%incendi%'" -limit 5
```

La ricerca è "contiene", non esatta. Restituisce gli stessi 190 record di `openrndt search --q incendi`.

## Ricerca spaziale — usala con sospetto

`BBOX` è l'unico operatore spaziale supportato e `-spat` funziona, ma **restituisce molti meno record del REST sulla stessa area**:

```bash
ogrinfo -ro -so "CSW:https://geodati.gov.it/RNDT/csw" records \
  -spat 13.2 38.0 13.5 38.2 -oo MAX_RECORDS=200
# Feature Count: 30
```

```bash
openrndt --format json search --bbox 13.2,38.0,13.5,38.2 --num 1 | jq .total
# 748
```

30 contro 748 sulla stessa bounding box (il conteggio CSW non cambia alzando `MAX_RECORDS`, quindi non è un effetto della paginazione). Non è chiaro se dipenda da semantiche diverse (`contains` invece di `overlaps`) o dall'ordine degli assi in EPSG:4326. **Per selezionare per area usa `openrndt --bbox`**: il filtro spaziale esiste anche nel REST ed è più inclusivo. Ricorri a `-spat` solo se ti serve la selezione già dentro un comando `ogr2ogr`, sapendo che è parziale.

## Export

**CSV** (per fogli di calcolo), selezionando i campi utili:

```bash
ogr2ogr -f CSV incendi.csv "CSW:https://geodati.gov.it/RNDT/csw" records \
  -where "anytext LIKE '%incendi%'" \
  -select "identifier,title,type,subject,modified" \
  -limit 20 -oo MAX_RECORDS=20
```

**GeoJSON** (mantiene la geometria bbox, gestisce nativamente i campi lista):

```bash
ogr2ogr -f GeoJSON palermo.geojson "CSW:https://geodati.gov.it/RNDT/csw" records \
  -spat 13.2 38.0 13.5 38.2 -limit 5 -oo MAX_RECORDS=5
```

**GeoPackage** (per QGIS) — richiede la conversione dei campi lista, altrimenti il file esce corrotto:

```bash
ogr2ogr -f GPKG palermo.gpkg "CSW:https://geodati.gov.it/RNDT/csw" records \
  -spat 13.2 38.0 13.5 38.2 -limit 5 -oo MAX_RECORDS=5 \
  -mapFieldType StringList=String
```

> Senza `-mapFieldType StringList=String` il GPKG viene scritto ma non è leggibile (`not recognized as being in a supported file format`): i campi `other_identifiers`/`other_subjects`/`other_references` sono `StringList`, non supportati nativamente dal driver GPKG.

## Opzioni utili

| Opzione | A cosa serve |
|---|---|
| `-limit N` | ferma la lettura a N feature (lato client) |
| `-oo MAX_RECORDS=N` | dimensione della pagina richiesta al server: tienila bassa nei test, il CSW è lento |
| `-oo ELEMENTSETNAME=full` | chiede il record completo invece del brief |
| `-oo FULL_EXTENT_RECORDS_AS_NON_SPATIAL=YES` | tratta come non spaziali i record con estensione "tutto il mondo" (molti record RNDT dichiarano una bbox che copre l'Italia intera o il globo: sono rumore in qualunque query spaziale) |
| `--config GML_SKIP_CORRUPTED_FEATURES YES` | prosegue invece di fermarsi sulle geometrie malformate |
| `--debug on` | stampa l'XML `GetRecords` che GDAL invia: utile per capire cosa viene realmente tradotto |

## Limiti del servizio (verificati)

- **`SortBy` è ignorato**: `DESC` e `ASC` restituiscono lo stesso ordine, benché il `GetCapabilities` dichiari `CoreSortables: Title, Modified`. Nessun ordinamento è possibile.
- **Nessun filtro per data**: le `Filter_Capabilities` dichiarano un solo operatore di confronto, `PropertyIsEqualTo` (più `BBOX`). Un `PropertyIsGreaterThanOrEqualTo` risponde «Operator … is not supported». `dct:modified` viene accettato ma punta alla data di reindicizzazione.
- **I queryables `apiso:*` non funzionano**: `apiso:identifier`, `apiso:type`, `apiso:CreationDate`, `apiso:TopicCategory`, `apiso:OrganisationName` non producono risultati. Funzionano solo i nomi Dublin Core (`anytext`, `dc:type`).
- **Zero risultati → risposta non valida**: il server emette `numberOfRecordsMatched="[object Object]"` invece di un numero.

> ⚠️ **La guida operativa ufficiale non è allineata al servizio.** La [guida CSW del RNDT](https://geodati.gov.it/geoportale/images/struttura/documenti/RNDT_guida_operativa_csw_v1.0.pdf) usa in tutti gli esempi `typeNames="gmd:MD_Metadata"` (il servizio dichiara solo `csw:Record`, `csw:SummaryRecord`, `csw:BriefRecord`) ed elenca in ALLEGATO A 28 queryables `apiso:*` che non funzionano. L'esempio §2.2.1 della guida, copiato alla lettera, restituisce **0 record** (i metadati Regione Liguria in catalogo sono 818). Non fidarti della guida: usa le ricette di questa pagina. Dettaglio in `ref/csw-rndt.md`.

## Regola pratica

Usa il CSW **solo** per portare il catalogo dentro un flusso GIS: aprirlo in QGIS (MetaSearch o il layer `records`) o esportarlo con `ogr2ogr` come GeoJSON/GPKG. Per qualunque ricerca — testo, data, area, ente, categoria, licenza — e per l'ordinamento, usa `openrndt` sull'API REST: è più completo su ogni singolo criterio, filtro spaziale incluso. Vedi [`search-syntax.md`](./search-syntax.md) e [`workflows.md`](./workflows.md).
