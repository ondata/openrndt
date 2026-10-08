---
type: External API
title: Form Ricerca Dettagliata del geoportale RNDT
description: Come la Ricerca Dettagliata di geodati.gov.it traduce ogni campo in una query per la REST, ricavato dal codice della pagina.
resource: https://geodati.gov.it/geoportale/ricerca-dettagliata
tags: [rndt, rest, lucene, geoportale, geolibre]
timestamp: 2026-09-26T00:00:00Z
---

La Ricerca Dettagliata non usa un'API propria. La funzione JavaScript `adaptSerialize()`, inline nella pagina, trasforma il form in una query `q=` Lucene più i parametri `bbox`, `spatialRel` e `sort`, e la manda alla stessa [API REST](rndt-rest-api.md) usata da openrndt, tramite un proxy PHP del portale (`services-advancedSearch.php`, che inoltra a `geoportal-catalog/rest/metadata/search` su un host interno). Letto dal codice il 2026-09-26. Una query composta dal form (testo, campo titolo, tipo dati, data di revisione con valori vuoti, bbox Intersects, ordinamento) è stata rigirata sulla REST pubblica con lo stesso esito: 1 record, «Alberi monumentali». La verifica è su **una** query, non su tutte le combinazioni.

Serve come specifica per il pannello RNDT di GeoLibre e per allineare le opzioni di [search](/cli/search.md).

# Campi e query generata

Tutte le clausole sono unite in `AND`.

| Campo del form | Nome nel form | Clausola generata |
|---|---|---|
| Cosa cercare: Tutti | `selection-search=all` | nessuna |
| Cosa cercare: Dati | `selection-search=dati` (+ `dati_dataset`, `dati_series`, entrambi attivi) | `apiso_Type_s:(dataset OR series)` |
| Cosa cercare: Servizi | `selection-search=servizi` | `(apiso_Type_s:service)` |
| Tipo di servizio (solo con Servizi) | `services-checkbox[]`: `view`, `download`, `discovery`, `transformation`, `invoke`, `other` | `apiso_ServiceType_s:(…)` |
| Testo libero, «Tutte le parole» | `text-free-radio=all` | parole unite da `AND` tra parentesi: `(alberi AND monumentali)` |
| Testo libero, «Almeno una parola» | `text-free-radio=one` | parole unite da `OR`: `(alberi OR monumentali)` |
| Testo libero, «Testo» | `text-free-radio=text` | il testo così com'è tra parentesi: è **Lucene grezzo**, non una frase esatta. «Ricerca tra» viene ignorato |
| Ricerca tra | `filter-search`: vuoto (Ovunque), `title`, `description`, `apiso_Lineage_txt`, `apiso_AccessConstraints_s` | prefisso di campo davanti al gruppo di parole: `title:(alberi AND monumentali)` |
| Parola chiave (separate da virgola) | `keywords` | `keywords_s:("a" OR "b")` |
| Amministrazione responsabile | `admin-resp` | `EnteResponsabile_s:"…"` (valore esatto, case-sensitive) |
| Categoria ISO | `tema-iso` | `apiso_TopicCategory_s:(a OR b)` |
| Temi INSPIRE (solo con Dati) | `inspireThemes` | `INSPIRETheme_s:("a" OR "b")` |
| Dataset prioritari (solo con Dati) | `tema-pdataset-prioritydataset` | `PriorityDataset_s:("…")` |
| Temi open data (solo con Dati) | `tema-pdataset-opendata` | `OpenDataTheme_s:("…")` |
| Solo open data (solo con Dati) | `tema_pdataset-checkbox-opendata_control` | `_exists_:isOpendata`. Al 2026-10-08 la casella separata non c'è più: il campo nascosto `OpenData` è legato al menu «Dati aperti» dei temi, ma il gestore cerca `name=tema_pdataset-checkbox-opendata` mentre le caselle si chiamano `…-opendata[]`, quindi non è detto che scatti (letto nel codice, non provato nell'interfaccia) |
| Ambito territoriale (solo con Dati) | `tema-pdataset-ambitoTerritoriale` | `AmbitoTerritoriale_s:("…")` |
| Dati di elevato valore (solo con Dati) | `tema-pdataset-datiElevatoValore` | `DatiElevatoValore_s:("…")` |
| Quando: tipo di data | `specialist-date`: `apiso_CreationDate_dt`, `apiso_PublicationDate_dt`, `apiso_RevisionDate_dt` (default Revisione) | `<campo>:[da TO a]`, con `1900-01-01` e `2100-12-31` se un estremo manca |
| Quando: «Considera valori vuoti» (attiva di default) | `specialist-date_search=true` | `(<campo>:[da TO a] OR (NOT _exists_:<campo>))` |
| Dove: Dovunque / Intersecanti | `spatialRel=all` / `Intersects` | `bbox=xmin,ymin,xmax,ymax&spatialRel=Intersects`; senza box nessun filtro |
| Ordina per | `order`: vuoto (Rilevanza), `title:asc`, `title:desc`, `apiso_Modified_dt:asc`, `apiso_Modified_dt:desc` | `sort=…` |

Se la prima clausola comincia con `(` il form antepone `* AND `. Sulla REST non cambia nulla: `(apiso_Type_s:service)` e `* AND (apiso_Type_s:service)` danno entrambi 3.164, e con `AND title:(acque)` entrambi 72 (verificato 2026-09-26).

# Area geografica

Le tre schede di «Dove» sono Area geografica, Disegna e Coordinate. L'area amministrativa viene da tre file statici del portale:

| File | Peso |
|---|---|
| `/geoportale//templates/rndt/advancedSearch/Regioni/Regioni.json` | 18 KB |
| `/geoportale//templates/rndt/advancedSearch/Province/Province.json` | 96 KB |
| `/geoportale//templates/rndt/advancedSearch/Comuni/Comuni.json` | 7,3 MB |

Sono FeatureSet Esri in EPSG:3857 (`wkid` 102100) con campi come `COD_REG` e `NOME_REG`. Le geometrie non sono confini ma **rettangoli** di cinque vertici: scegliere una regione equivale a filtrare per la sua bbox. La mappa carica anche i limiti amministrativi ISPRA 2012 (`sinacloud.isprambiente.it/arcgisina/rest/services/cs_site/limitiamministrativi_2012/MapServer/0`), usati per la visualizzazione.

# Note per chi replica il form

* Il filtro data con «Considera valori vuoti» nel codice attuale include i record senza quel campo: sul caso dell'issue #9 (`incendi`, Creazione 2024-01-01/2026-07-18) la query con la casella dà 111 contro i 15 senza. L'issue descriveva la versione del 2026-07-18, che metteva in AND tutti e tre i campi data. La correzione è vista nel codice e misurata sulla REST, non ancora riprovata nell'interfaccia (vedi [bug noti](known-issues.md)).
* I filtri tematici (INSPIRE, prioritari, open data, ambito, elevato valore) valgono solo con «Dati»: passando a «Servizi» il form li scarta.
* Il portale respinge il browser headless con user agent di default («App offline», con codice errore); con uno user agent desktop si apre. Un overlay di caricamento (`#loadingSelectTotal`) resta attivo in headless e blocca i clic, quindi il comportamento è stato ricavato dal codice e non compilando il form.

# Citations

[1] Pagina: https://geodati.gov.it/geoportale/ricerca-dettagliata, letta il 2026-09-26 (funzioni `adaptSerialize`, `replaceText`, `createObjUrl`).
