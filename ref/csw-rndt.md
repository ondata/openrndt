# Servizio di ricerca CSW del RNDT — documentazione ufficiale e verifiche

Pagina di origine: <https://geodati.gov.it/geoportale/strumenti/2015-04-21-22-41-05> (voce di menu "Servizio di ricerca - CSW")
Data pagina: 27/02/2013 · **Ultima modifica dichiarata: 25/05/2026**
Endpoint: <https://geodati.gov.it/RNDT/csw>
Copia acquisita e verifiche: 2026-07-17

## Cosa dichiara la pagina ufficiale

Il servizio di ricerca del RNDT consente di ricercare, attraverso client esterni, i set di dati territoriali e i servizi relativi in base al contenuto dei metadati, secondo la Direttiva INSPIRE e il Regolamento (CE) 976/2009.

> «Il servizio è basato sulle Specifiche OGC "Catalogue Services Specification 2.0.2 - ISO Metadata Application Profile" ed è **conforme alle prescrizioni della guida tecnica INSPIRE "Technical Guidance for the implementation of INSPIRE Discovery Services, v. 3.1"**.»

Il punto di connessione è `https://geodati.gov.it/RNDT/csw`. La pagina rimanda a un client CSW dedicato, al documento di GetCapabilities e a una guida operativa nella sezione "Archivio documenti".

## GetCapabilities — cosa dichiara il server

Operazioni supportate: `GetCapabilities`, `DescribeRecord`, `GetRecords`, `GetRecordById`.

| Vincolo dichiarato | Valore |
|---|---|
| `CoreQueryables` | `AnyText`, `BoundingBox` |
| `CoreSortables` | `Title`, `Modified` |
| `DefaultSortingAlgorithm` | `relevance` |
| `Filter-CQL` | `false` |
| `Filter-FES-KVP-Advanced` | `false` |
| `Transaction` | `false` |
| `OpenSearch` | `true` |
| `OpenSearchDescriptionDocument` | `http://192.168.3.34:8080/geoportal-catalog/opensearch/description` |

## Cosa funziona (verificato)

- **Ricerca full-text** via `PropertyIsLike` su `AnyText`: `*incendi*` → 295 record.
- **`GetRecordById`**: restituisce l'ISO 19139 completo (≈37 KB per record), utile per l'harvesting del metadato integrale.
- **Integrazione GDAL/OGR**: il driver CSW funziona, es. `ogrinfo -ro -al "CSW:https://geodati.gov.it/RNDT/csw" -where "subject LIKE 'salute'"` e l'export con `ogr2ogr -F csv … -oo ELEMENTSETNAME=full -oo MAX_RECORDS=500` (ricetta: <https://arigadicomando.it/gdal-ogr/ricette/#interrogare-un-server-csw>).

## Cosa NON funziona (verificato 2026-07-17)

### `SortBy` ignorato, in contraddizione con le capabilities dichiarate

Il server dichiara `CoreSortables: [Title, Modified]`, ma una `GetRecords` con `<ogc:SortBy>` su `apiso:Modified` in `DESC` e in `ASC` restituisce **lo stesso ordine** (stessi primi ID: `age:D_E973_MARSAGLIA`, `R_SARDEG:393f76de-…`, `age:D_F155_MESERO`). L'ordinamento non è applicato. Non conforme alla INSPIRE TG Discovery Services v3.1, che la pagina ufficiale dichiara di rispettare. Issue #5.

### Filtro per data: o eccezione, o semanticamente sbagliato

- `PropertyIsBetween` su `apiso:Modified`, `apiso:CreationDate`, `dc:date` → eccezione `InvalidParameterValue`.
- `PropertyIsBetween` su `dct:modified` → **accettato, ma filtra sulla data di reindicizzazione del catalogo**, non sulla data del metadato.

Prova decisiva (confronto CSW vs REST sullo stesso criterio temporale):

| Intervallo | CSW `dct:modified` | REST `apiso_Modified_dt` (data reale del metadato) |
|---|---|---|
| aprile 2026 | 21.288 | 437 |
| **solo 2026-04-25** | **21.288** (identico ad aprile) | — |
| giugno 2026 | 765 | 85 |
| **2025 (anno intero)** | **0** | **10.637** |

I 21.288 record collassano tutti sul singolo giorno 2026-04-25, cioè il timestamp dell'ultima reindicizzazione. Conseguenza: un client che chiede "record modificati nel 2025" riceve **zero** mentre nel catalogo ce ne sono 10.637. Per l'harvesting incrementale — il caso d'uso principale del CSW — il servizio è inutilizzabile: o si riscarica tutto (tutti i record hanno la stessa data di reindex) o non si ottiene nulla.

### Risposta non valida quando i risultati sono zero

Con zero risultati il server emette:

```xml
<csw:SearchResults numberOfRecordsMatched="[object Object]" numberOfRecordsReturned="0" nextRecord="-1" …/>
```

`numberOfRecordsMatched` è tipizzato `nonNegativeInteger` nello schema CSW 2.0.2: `[object Object]` rende la risposta non valida e rompe i client conformi. È la stessa causa del `total` di tipo variabile sull'API REST (l'oggetto Elasticsearch `{value, relation}` serializzato senza estrarre `value`).

### IP interno nelle capabilities

Il documento di GetCapabilities pubblicizza l'OpenSearch description a `http://192.168.3.34:8080/geoportal-catalog/opensearch/description`, indirizzo privato irraggiungibile. Issue #2 si propaga quindi nei metadati del servizio di discovery INSPIRE.

## La guida operativa ufficiale descrive un servizio diverso da quello attivo

Guida: **RNDT — Guida operativa all'uso del servizio di ricerca (CSW)**, v1.0, 18 pagine
<https://geodati.gov.it/geoportale/images/struttura/documenti/RNDT_guida_operativa_csw_v1.0.pdf>
Copia locale: `RNDT_guida_operativa_csw_v1.0.pdf` (+ conversione `RNDT_guida_operativa_csw_v1.0.md`, ottenuta con `lit parse --format markdown`).

Confrontando la guida con il servizio in esercizio (2026-07-17) emergono incoerenze sistematiche.

### 1. `typeNames="gmd:MD_Metadata"` non è supportato

Tutti gli esempi di `GetRecords` della guida (§2.2.1, §2.2.2, §2.2.3) usano `<csw:Query typeNames="gmd:MD_Metadata">`. Il `GetCapabilities` del servizio dichiara però solo:

```
typeName: csw:Record, csw:SummaryRecord, csw:BriefRecord
```

### 2. I 28 queryables dell'ALLEGATO A non funzionano

L'ALLEGATO A (Tab. 3) elenca come interrogabili, fra gli altri: `apiso:identifier`, `apiso:type`, `apiso:title`, `apiso:CreationDate`, `apiso:PublicationDate`, `apiso:RevisionDate`, `apiso:TopicCategory`, `apiso:OrganisationName`, `apiso:AccessConstraints`, `apiso:OtherConstraints`, `apiso:TempExtent_begin`, `apiso:TempExtent_end`, `apiso:AnyText`.

Verifica: **nessuno dei nomi con prefisso `apiso:` produce risultati**; funzionano solo i nomi Dublin Core.

| Filtro provato | Esito |
|---|---|
| `PropertyIsLike` su `AnyText` | ✅ 190 record (`%incendi%`) |
| `PropertyIsEqualTo` su `dc:type` = `service` | ✅ 19.145 record |
| `PropertyIsLike` su `apiso:AnyText` | ❌ nessun risultato/eccezione |
| `PropertyIsEqualTo` su `apiso:type` | ❌ |
| `PropertyIsEqualTo` su `apiso:TopicCategory` | ❌ |
| `PropertyIsEqualTo` su `apiso:OrganisationName` | ❌ |
| `PropertyIsLike` su `apiso:identifier` | ❌ 0 record |

Il `GetCapabilities` conferma il disallineamento: dichiara `CoreQueryables: AnyText, BoundingBox` — due elementi contro i 28 della guida.

### 3. Nessun operatore per le date

L'ALLEGATO A presuppone l'interrogabilità di quattro campi data, ma le `Filter_Capabilities` dichiarano **un solo operatore di confronto, `PropertyIsEqualTo`** (più `BBOX` come operatore spaziale). Un filtro con `PropertyIsGreaterThanOrEqualTo` risponde:

```xml
<Exception exceptionCode="InvalidParameterValue" locator="PropertyIsGreaterThanOrEqualTo">
  <ExceptionText>Operator ogc:PropertyIsGreaterThanOrEqualTo is not supported.</ExceptionText>
</Exception>
```

Con solo `EqualTo` un filtro temporale per intervallo è impossibile.

### 4. Esempio riproducibile: la §2.2.1 della guida restituisce 0 record

Richiesta copiata **alla lettera** dalla guida (§2.2.1: «vengono ricercati dati e servizi per cui il metadato corrispondente all'identificatore del file inizia per `r_ligur`»):

```bash
curl -s -X POST -H "Content-Type: application/xml; charset=UTF-8" -d '<?xml version="1.0" encoding="UTF-8"?><csw:GetRecords service="CSW" version="2.0.2" outputFormat="application/xml" outputSchema="http://www.isotc211.org/2005/gmd" resultType="results" xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:ogc="http://www.opengis.net/ogc" xmlns:apiso="http://www.opengis.net/cat/csw/apiso/1.0" xmlns:gmd="http://www.isotc211.org/2005/gmd"><csw:Query typeNames="gmd:MD_Metadata"><csw:ElementSetName>full</csw:ElementSetName><csw:Constraint version="1.1.0"><ogc:Filter><ogc:PropertyIsLike wildCard="%" singleChar="_" escapeChar="/"><ogc:PropertyName>apiso:identifier</ogc:PropertyName><ogc:Literal>r_ligur%</ogc:Literal></ogc:PropertyIsLike></ogc:Filter></csw:Constraint></csw:Query></csw:GetRecords>' \
  https://geodati.gov.it/RNDT/csw
```

Risposta:

```xml
<csw:SearchResults numberOfRecordsMatched="[object Object]" numberOfRecordsReturned="0" nextRecord="-1" …/>
```

Zero record. Ma i record della Regione Liguria nel catalogo sono **818** (verificato via REST: `q=fileid:r_liguri*` → 818, primo id `r_liguri:D.1433`). L'esempio ufficiale della guida non funziona sul servizio ufficiale, e per di più restituisce `[object Object]` al posto del conteggio.

## Conclusione: il CSW supera i limiti dell'API REST?

**No.** Riepilogo:

| Problema | REST | CSW |
|---|---|---|
| Ordinamento per data | solo `apiso_Modified_dt` (data della scheda) | **nessuno**: `SortBy` ignorato pur essendo dichiarato |
| Filtro per data del metadato | ✅ `q=apiso_PublicationDate_dt:[…]` funziona | ❌ eccezione su `apiso:*`; `dct:modified` filtra la data di reindex |
| Ricerca full-text | ✅ | ✅ |
| Recupero metadato completo | ✅ (`item/{id}/xml`) | ✅ (`GetRecordById`) |
| Aggregazioni/facet | ❌ | ❌ |

### Cosa il CSW aggiunge davvero rispetto al REST

Verificato 2026-07-17, per non attribuire al CSW valore che non ha:

- **Ricerca full-text: nessun vantaggio.** CSW `PropertyIsLike` su `AnyText` con `%incendi%` → 190 record; REST `q=incendi` → 190. Stesso risultato.
- **Recupero del metadato: nessun vantaggio.** `GetRecordById` e `rest/metadata/item/{id}/xml` restituiscono file **byte-identici** (stesso MD5 `019aa2bc…`, 26.812 byte su `ispra_rm:01IdroHazard_DT`).
- **Interoperabilità: qui sta l'unico vantaggio reale.** Il CSW è consumabile da client che non parlano l'API REST proprietaria: driver `CSW:` di GDAL/OGR (`ogrinfo`, `ogr2ogr`), QGIS MetaSearch, OWSLib/pycsw, harvester INSPIRE.

In sintesi: come *sorgente dati* il CSW non offre nulla che il REST non dia già, e su filtri e ordinamento è nettamente inferiore. Ha senso solo come **superficie di interoperabilità standard** per strumenti GIS. Per qualunque interrogazione conviene l'API REST con la sintassi Lucene `q=campo:[range]`.
