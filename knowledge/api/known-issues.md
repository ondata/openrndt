---
type: Reference
title: Bug noti dell'API RNDT
description: Divergenze verificate live tra la documentazione ufficiale RNDT e il comportamento reale dell'API.
tags: [rndt, bug, verificato-live]
timestamp: 2026-08-29T00:00:00Z
---

Tutti i punti seguenti sono stati verificati empiricamente contro l'API di produzione, non dedotti dalla documentazione. openrndt li compensa dove possibile. Ultima riverifica completa: **2026-08-29**, catalogo a 23.738 record.

# Divergenze

| Comportamento documentato | Comportamento reale | Compensazione in openrndt |
|---------------------------|---------------------|---------------------------|
| Il parametro `dataCategory` filtra per categoria. | Non filtra: ritorna sempre il catalogo intero. | `--data-category` è tradotto nella clausola Lucene `q=keywords_s:VAL` (`OR` per valori multipli). |
| `sort=dateDescending` / `dateAscending` ordinano per data. | Ignorati: ordine identico fra loro (riconfermato 2026-07-17). | `discover --what sort_values` marca i valori rotti; la sintassi funzionante è `campo:asc\|desc` su campo sortable (es. `apiso_Modified_dt:desc`). |
| — | Ordinare su un campo `text` analizzato (es. `title` nudo) dava errore Elasticsearch "Fielddata is disabled"; **dal 2026-07-17 risulta funzionare** (`title:asc` ordina alfabeticamente — comportamento API cambiato). | Documentato nelle codelist; i campi garantiti sortable restano `_s`/`_dt`/`_i`. |
| Esiste una data di pubblicazione ordinabile. | `apiso_PublicationDate_dt` **esiste** (8.457/23.738 record, ~36%; riverificato 2026-08-29) ed è **filtrabile** via `q=apiso_PublicationDate_dt:[range]`, ma **non ordinabile** (`sort=…` ignorato, come `apiso_RevisionDate_dt`). Verificato live 2026-07-17 — corregge la nota precedente che lo dava per "inesistente". `apiso_CreationDate_dt` spesso null/parziale. | Proxy per "più recenti": `apiso_Modified_dt:desc`. Per *filtrare* (non ordinare) per data di pubblicazione: `q=apiso_PublicationDate_dt:[…]` (issue #4). |
| Il filtro per data della Ricerca Dettagliata rispetta il tipo di data scelto. | Mette in AND tutti e 3 i campi data; i record privi di uno di essi sono scartati anche con "Considera valori vuoti" spuntato. Es. "incendi creati dal 2024": 15 reali, portale 0. | Bug del frontend ufficiale, non della CLI (issue #9). |
| L'endpoint CSW supporta `SortBy` (INSPIRE Discovery Services v3.1). | `SortBy` ignorato: non conforme. | Nessuna: documentato (issue #5 del repository). |
| Il campo top-level `updated` di ogni risultato è la data di aggiornamento del metadato. | È `_source.sys_modified_dt`: l'istante di **indicizzazione** nel catalogo, raggruppato per batch di reindicizzazione (verificato 2026-08-09: record con `updated 2026-04-25T15:37:34Z` e `apiso_Modified_dt 2019-11-13`). Varia per record, quindi non è riconoscibile come costante. | Negli output `table`/`csv`/`compact`/`footprints` il campo si chiama `indexed`, mentre `updated` è `apiso_Modified_dt` — lo stesso campo su cui filtrano `--updated-from/--updated-to`. Con `--format json` (passthrough) resta la convenzione dell'API, ricordata su stderr. |
| L'API supporta aggregazioni/facet sui campi indicizzati. | `facet=<campo>` è **ignorato in silenzio**: la risposta ha esattamente le stesse chiavi con e senza (verificato 2026-08-09). Non c'è modo di chiedere al server i valori distinti di un campo. | `organization_names()` aggrega i nomi di ente a valle su un campione di risultati; è così che `--org` con zero risultati suggerisce i nomi realmente in catalogo. |
| Una `bbox` malformata produce un errore. | Viene **ignorata in silenzio**: `bbox=non,valido` e `bbox=12,45,11` (tre valori) restituiscono il catalogo intero, 23.738 record, con HTTP 200. Una bbox invertita (`12,45,11,44`) o fuori range fa invece rispondere 500. Verificato 2026-08-29. | Dalla 3.1.0 `search` e `footprints` validano la bbox prima della chiamata (quattro valori numerici, longitudini -180..180, latitudini -90..90, `xmin < xmax`, `ymin < ymax`) e escono con codice 2. |
| I dati a licenza aperta sono selezionabili da un campo. | La licenza sta in tre campi diversi a seconda del record (`isOpendata`, `apiso_AccessConstraints_s`, `apiso_OtherConstraints_s`), nessuno sempre valorizzato, e i valori non sono normalizzati: su 3000 record `isOpendata` è presente sul 72% (55% escludendo l'Agenzia delle Entrate, che da sola ne vale 1177) e in un terzo dei casi contiene il solo marcatore `opendata`. Quattro formulazioni ragionevoli della stessa domanda danno 16.759, 10.534, 3.760 e 14.050. Verificato 2026-08-29. | Dalla 3.1.0 gli output espongono `open` e `license` presi da `isOpendata` **senza normalizzare**, con la copertura dichiarata: `open=false` significa «l'ente non l'ha dichiarato lì», non «dato chiuso». Un conteggio dei dati aperti va sempre accompagnato dal campo usato. |
| Gli esempi della guida operativa CSW funzionano sul servizio. | L'esempio §2.2.1 (`apiso:identifier` che inizia per `r_ligur`) restituisce **0 record**, mentre via REST la Liguria ne ha 824. I `CoreQueryables` dichiarati sono solo `AnyText` e `BoundingBox`, l'unico operatore di confronto è `PropertyIsEqualTo`, `GetDomain` è dichiarato non supportato. Riverificato 2026-08-29. | Nessuna: per cercare si usa l'API REST. Il CSW serve solo a portare il catalogo in un flusso GIS (vedi `references/csw.md` della skill). |
| Item inesistente → errore HTTP. | Risponde `200` con body `{"found": false}`. | `get_item` controlla `found` e solleva `ItemNotFoundError`. |

# Semantica dei campi ente (verificata 2026-08-09)

Tre campi diversi per la stessa informazione, con comportamenti di ricerca incompatibili:

| Campo | Tipo | Comportamento |
|---|---|---|
| `apiso_OrganizationName_txt` | analizzato | La ricerca per frase è case-insensitive e insensibile all'ordine dei token: `"comune di torino"` → 269 record, un solo ente. È il campo usato da `--org`. |
| `EnteResponsabile_s` | keyword | Confronto esatto e **case-sensitive**: `"Comune di Torino"` → 269, `"comune di torino"` → 0. Campo di `--org-exact`. |
| `contact_organizations_s` | keyword, array | Case-sensitive **e** over-matching con wildcard: `*bologna*` → 0, `*Bologna*` → 110 (erano 112 il 2026-08-09) di cui nessuno del Comune di Bologna: sono di Regione Emilia-Romagna, Città metropolitana, ARSTPC e ARPAE. Da evitare per la ricerca per ente. |

Un ente assente da tutti e tre non è un difetto di query: il Comune di Bologna dà 0 ovunque perché non pubblica in proprio (i suoi rilievi entrano in catalogo sotto Regione Emilia-Romagna). L'associazione ruolo→organizzazione dell'ISO 19115 non è esposta nell'indice; segnalato ad AgID il 2026-08-09.

# Problemi di qualità dei dati (non dell'API)

- Alcuni record dichiarano una bbox errata che copre tutta l'Italia (`6.6,35.5,18.5,47.1`): compaiono come rumore in qualunque ricerca `--bbox`. Il filtro bbox in sé funziona (semantica overlaps, verificata).

# Citations

[1] `ref/rest-api-rndt.md` e `LOG.md` nel repository (verifiche live datate).
[2] [Pagina ufficiale REST API RNDT](https://geodati.gov.it/geoportale/eng/strumenti-en/rest-api)

# Segnalazioni ad AgID e loro stato

Inviate a `info@rndt.gov.it` con Antonio Rotundo in copia il **18 luglio 2026** (punti 1-6) e il
**10 agosto 2026** (punto 7). Risposta del 20 luglio: «Le analizzeremo con il fornitore per poterle
risolvere e dartene comunicazione». Riverificate una per una il **2026-08-29**: risolta la quarta.

| # | Segnalazione | Stato al 2026-08-29 |
|---|---|---|
| 1 | «Considera valori vuoti» della Ricerca Dettagliata esclude i record con date vuote invece di includerli | aperta: query del solo campo creazione 15 record, query con i tre campi in AND 0 |
| 2 | `sort` su `apiso_PublicationDate_dt` non ha effetto; `sort=title` senza direzione dà 500 | aperta: gli id restituiti sono identici a quelli senza ordinamento, e `title` risponde ancora 500 |
| 3 | Gli esempi della guida operativa CSW non funzionano; `SortBy` ignorato | aperta, con un miglioramento: il conteggio di una ricerca a vuoto era `[object Object]`, ora è `numberOfRecordsMatched="0"`, valore valido per lo schema |
| 4 | I link `rel="alternate"` contengono l'IP privato `192.168.3.34:8080` | **risolta**: i link escono su `https://geodati.gov.it/geoportal-catalog/...` e l'IP non compare più nemmeno nel GetCapabilities del CSW |
| 5 | `dataCategory` non filtra | aperta: `dataCategory=planningCadastre` → 23.738, cioè il catalogo intero |
| 6 | Nessun modo affidabile di selezionare i dati a licenza aperta; nessuna aggregazione | aperta: nessun campo di licenza normalizzato è comparso, `facet` resta ignorato |
| 7 | La ricerca per ente funziona solo se l'ente si è dichiarato: il Comune di Bologna è invisibile | aperta: 0 su tutte e tre le forme, mentre Torino resta a 271 e Genova a 144 |
