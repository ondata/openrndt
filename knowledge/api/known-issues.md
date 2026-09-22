---
type: Reference
title: Bug noti dell'API RNDT
description: Divergenze verificate live tra la documentazione ufficiale RNDT e il comportamento reale dell'API.
tags: [rndt, bug, verificato-live]
timestamp: 2026-09-04T00:00:00Z
---

Tutti i punti seguenti sono stati verificati empiricamente contro l'API di produzione, non dedotti dalla documentazione. openrndt li compensa dove possibile. Ultima riverifica completa: **2026-09-04**, catalogo a 23.741 record.

# Divergenze

| Comportamento documentato | Comportamento reale | Compensazione in openrndt |
|---------------------------|---------------------|---------------------------|
| Il parametro `dataCategory` filtra per categoria. | Non filtra: ritorna sempre il catalogo intero. Dal 31/07/2026 non è più elencato nella pagina ufficiale. | `--data-category` è tradotto nella clausola Lucene `q=keywords_s:VAL` (`OR` per valori multipli). |
| `sort=dateDescending` / `dateAscending` ordinano per data. | Ignorati: ordine identico fra loro (riconfermato 2026-09-04). Dal 31/07/2026 la pagina ufficiale documenta solo `apiso_Modified_dt:asc\|desc`, `title:asc\|desc` e `relevance`. | `discover --what sort_values` marca i valori rotti; la sintassi funzionante è `campo:asc\|desc` su campo sortable (es. `apiso_Modified_dt:desc`). |
| — | `sort=title` senza direzione risponde 400 con l'errore Elasticsearch "Fielddata is disabled on [title]" (riverificato 2026-09-04); `title:asc` e `title:desc` ordinano (ordine per byte: minuscole dopo le maiuscole). Dal 31/07/2026 la pagina ufficiale dice che la direzione è obbligatoria. | Documentato nelle codelist; i campi garantiti sortable restano `_s`/`_dt`/`_i`. |
| Esiste una data di pubblicazione ordinabile. | `apiso_PublicationDate_dt` **esiste** (8.457/23.738 record, ~36%; riverificato 2026-08-29) ed è **filtrabile** via `q=apiso_PublicationDate_dt:[range]`, ma **non ordinabile** (`sort=…` ignorato, come `apiso_RevisionDate_dt`). Verificato live 2026-07-17 — corregge la nota precedente che lo dava per "inesistente". `apiso_CreationDate_dt` spesso null/parziale. | Proxy per "più recenti": `apiso_Modified_dt:desc`. Per *filtrare* (non ordinare) per data di pubblicazione: `q=apiso_PublicationDate_dt:[…]` (issue #4). |
| Il filtro per data della Ricerca Dettagliata rispetta il tipo di data scelto. | Mette in AND tutti e 3 i campi data; i record privi di uno di essi sono scartati anche con "Considera valori vuoti" spuntato. Es. "incendi creati dal 2024": 15 reali, portale 0. | Bug del frontend ufficiale, non della CLI (issue #9). |
| L'endpoint CSW supporta `SortBy` (INSPIRE Discovery Services v3.1). | `SortBy` ignorato: non conforme. | Nessuna: documentato (issue #5 del repository). |
| Il campo top-level `updated` di ogni risultato è la data di aggiornamento del metadato. | È `_source.sys_modified_dt`: l'istante di **indicizzazione** nel catalogo, raggruppato per batch di reindicizzazione (verificato 2026-08-09: record con `updated 2026-04-25T15:37:34Z` e `apiso_Modified_dt 2019-11-13`). Varia per record, quindi non è riconoscibile come costante. | Negli output `table`/`csv`/`compact`/`footprints` il campo si chiama `indexed`, mentre `updated` è `apiso_Modified_dt` — lo stesso campo su cui filtrano `--updated-from/--updated-to`. Con `--format json` (passthrough) resta la convenzione dell'API, ricordata su stderr. |
| L'API supporta aggregazioni/facet sui campi indicizzati. | `facet=<campo>` è **ignorato in silenzio**: la risposta ha esattamente le stesse chiavi con e senza (verificato 2026-08-09). Non c'è modo di chiedere al server i valori distinti di un campo. | `organization_names()` aggrega i nomi di ente a valle su un campione di risultati; è così che `--org` con zero risultati suggerisce i nomi realmente in catalogo. |
| Una `bbox` malformata produce un errore. | Viene **ignorata in silenzio**: `bbox=non,valido` e `bbox=12,45,11` (tre valori) restituiscono il catalogo intero, 23.738 record, con HTTP 200. Una bbox invertita (`12,45,11,44`) o fuori range fa invece rispondere 500. Verificato 2026-08-29. | Dalla 3.1.0 `search` e `footprints` validano la bbox prima della chiamata (quattro valori numerici, longitudini -180..180, latitudini -90..90, `xmin < xmax`, `ymin < ymax`) e escono con codice 2. |
| I dati a licenza aperta sono selezionabili da un campo. | La licenza sta in tre campi diversi a seconda del record (`isOpendata`, `apiso_AccessConstraints_s`, `apiso_OtherConstraints_s`), nessuno sempre valorizzato, e i valori non sono normalizzati: su 3000 record `isOpendata` è presente sul 72% (55% escludendo l'Agenzia delle Entrate, che da sola ne vale 1177) e in un terzo dei casi contiene il solo marcatore `opendata`. Quattro formulazioni ragionevoli della stessa domanda danno 16.759, 10.534, 3.760 e 14.050. Verificato 2026-08-29. | Dalla 3.1.0 gli output espongono `open` e `license` presi da `isOpendata` **senza normalizzare**, con la copertura dichiarata: `open=false` significa «l'ente non l'ha dichiarato lì», non «dato chiuso». Un conteggio dei dati aperti va sempre accompagnato dal campo usato. |
| Gli esempi della guida operativa CSW funzionano sul servizio. | **Dal 2026-09-04 l'esempio §2.2.1 funziona** (824 record, come via REST) e il GetCapabilities dichiara `SupportedISOQueryables`/`AdditionalQueryables` con i nomi dell'Allegato A (case-sensitive: `apiso:title` sì, `apiso:Title` no). Restano: `SortBy` ignorato, `PropertyIsBetween`/`GreaterThanOrEqualTo` «not supported» (niente filtro per intervallo di date), `constraint` in KVP **ignorato in silenzio** (qualunque vincolo → catalogo intero; in POST XML funziona), `GetDomain` non supportato. | Nessuna: per cercare si usa l'API REST. Il CSW serve solo a portare il catalogo in un flusso GIS (vedi `references/csw.md` della skill). |
| Fra termini separati da spazio in `q` l'operatore implicito è AND (come in Lucene standard). | È **OR**: `catasto siciliana` → 8.903, identico a `catasto OR siciliana`; `catasto AND siciliana` → 1. Verificato 2026-08-30. | Documentato in `discover --what search_params` (corretto: fino alla 3.1.0 diceva «AND implicito»). Per restringere scrivere `AND` esplicito. |
| Un servizio che risponde 200 al GetCapabilities serve mappe. | Non sempre: il WMS PCN della Carta Geologica (`wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/Vettoriali/Carta_geologica.map`) risponde 200 al GetCapabilities e `ServiceException` a ogni GetMap (MapServer non raggiunge il proprio PostGIS). Verificato 2026-08-30. | `resources` resta un check del GetCapabilities; il controllo con GetMap reale è nella skill (`ogc-services.md`). |
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

Inviate a `info@rndt.gov.it` con Antonio Rotundo in copia il **18 luglio 2026** (punti 1-6) e il **10 agosto 2026** (punto 7). Risposte di Rotundo: 20 luglio («le analizzeremo con il fornitore»), 4 settembre (regola dell'owner con nome IPA obbligatorio e verificato; il caso Bologna girato a Regione E-R; sui punti precedenti «ci hanno lavorato»; documento unico gradito). Documento unico in `docs/segnalazioni-rndt-agid.md` (Quarto → docx con `references/reference.docx`, entrambi gitignored), da riverificare nella prima settimana di ottobre 2026.

Riverificate una per una il **2026-09-04** (catalogo a 23.741 record):

| # | Segnalazione | Stato al 2026-09-04 |
|---|---|---|
| 1 | «Considera valori vuoti» della Ricerca Dettagliata esclude i record con date vuote invece di includerli | aperta: solo campo creazione 15, tre campi in AND 0 |
| 2 | `sort` su `apiso_PublicationDate_dt` non ha effetto; valori documentati non funzionanti | **documentazione risolta** (pagina del 31/07 con i soli valori reali); resta l'assenza di un ordinamento per data del dato; `sort=title` nudo ancora 400 |
| 3 | Gli esempi della guida operativa CSW non funzionano; `SortBy` ignorato | **in parte risolta**: esempio §2.2.1 → 824, queryables apiso dichiarati e funzionanti, conteggio a vuoto `"0"`; restano `SortBy`, nessun operatore di intervallo, `constraint` KVP ignorato (nuovo: a luglio dava 0, ora catalogo intero), guida ancora v1.0 |
| 4 | I link `rel="alternate"` contengono l'IP privato `192.168.3.34:8080` | **risolta** |
| 5 | `dataCategory` non filtra | **risolta per via documentale**: il parametro non filtra ancora ma non è più in pagina |
| 6 | Nessun modo affidabile di selezionare i dati a licenza aperta; nessuna aggregazione | aperta: 16.762 / 10.536 / 3.761 / 14.053; `facet` ignorato |
| 7 | La ricerca per ente funziona solo se l'ente si è dichiarato; ruolo scollegato dall'organizzazione | chiarita la regola owner/IPA; aperta la parte API (ruolo → organizzazione, campo IPA, facet). Bologna 0, Torino 271, Genova 144 |

Nel documento unico sono entrate anche quattro osservazioni nuove (bbox malformata ignorata: `non,valido` e tre valori → 200 e catalogo intero, invertita → 500; `updated` = `sys_modified_dt`; operatore implicito OR; item inesistente → 200 `found:false`) e tre note sulla pagina aggiornata: `keyword_s` e `isOpenData` scritti male (i nomi reali sono `keywords_s` e `isOpendata`, case-sensitive, con quelli in pagina → 0); il nuovo parametro `modified=da,a` filtra su `sys_modified_dt` e non su `apiso_Modified_dt` (`2025-01-01,2025-12-31` → 0 contro 10.424; `2026-04-25,2026-04-26` → 19.050 = ultima reindicizzazione); `num` dichiarato max 5000 ma 6000 risponde 200 con 6.000 risultati.
