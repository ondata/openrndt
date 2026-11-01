---
type: CLI Command
title: openrndt get
description: Recupera il dettaglio di un singolo metadato per ID, in JSON, XML ISO 19139 o HTML.
tags: [cli, get, metadata]
timestamp: 2026-07-17T00:00:00Z
---

Interroga l'endpoint [/rest/metadata/item/{id}](/api/rndt-rest-api.md). L'ID (es. `age:D_E973_MARSAGLIA`) viene URL-encodato integralmente (`quote(safe="")`), quindi gli ID con `:` o caratteri speciali sono sicuri.

# Opzioni

| Opzione | Significato |
|---------|-------------|
| `ITEM_ID` (argomento) | ID del metadato, tipicamente ottenuto da [search](/cli/search.md). |
| `--xml` | XML ISO 19139 grezzo (`gmd:MD_Metadata`). |
| `--html` | HTML pronto da renderizzare. |
| `--raw` | Busta Elasticsearch grezza (`_source` + flag), comportamento ante 3.3.0. |
| `--map-link/--no-map-link` | Calcola (default) o salta `geolibre_map_url`, che richiede di leggere le capabilities dei servizi della scheda. |

`--xml` e `--html` sono mutuamente esclusivi, e `--raw` non si combina con nessuno dei due (riguarda solo l'output JSON). Con `--format json` (default) dalla 3.3.0 `get` restituisce il **documento normalizzato**: gli stessi campi delle risposte di `search` (dalla 3.5.0 anche `geolibre_url`, il record aperto in GeoLibre web: vedi [search](/cli/search.md)) più email di contatto, bbox, lineage e data del dato (schema in [result-structure.md](/skill/rndt-explorer/references/result-structure.md)); `_source` è preservato per chi lo usa. `--raw` ripristina la busta Elasticsearch completa, vista che contiene i `links` alle risorse fruibili (WMS, WFS, download diretto).

# `geolibre_map_url` (dalla 3.12.0)

Subito dopo `geolibre_url`: lo stesso record aperto in GeoLibre web con il suo layer già sulla mappa (`rndtLayer`). `get` legge i layer di WMS e WMTS come [`resources --layers`](/cli/resources.md) e sceglie come il plugin (`wantedLayer`): il layer nominato da un link della scheda (`LAYERS=`), altrimenti l'unico candidato, altrimenti quello col titolo più vicino a quello della scheda (nessuna scelta per titolo su una scheda di tipo `service`). Candidati: WMTS in griglia Web Mercator con CORS sulle tile, WMS https offerti in EPSG:3857. GeoLibre 3.5 sa disegnare la mappa in altri sistemi, ma il link la apre in Web Mercator. Nessun candidato o servizio che non risponde → `null`, `get` non fallisce. Anche `geolibre_url` di `get` usa l'`_id` del catalogo, non il fileid.

# Id e fileid

Di solito coincidono, ma non sempre: le tre ortofoto AGEA hanno `_id` `agea:OI:DATEVOLO:m001+-++-+2026-09-25+12:42:55` e fileid `agea:OI:ORTOIMMAGINI:m004` (2023 e 2024 lo stesso). L'endpoint item vuole l'`_id`. Dalla 3.12.0, se l'id non c'è, `get` (e `search --id`) cerca `fileid:"<id>"` e usa l'`_id` trovato; con più schede `AmbiguousItemIdError`, con nessuna il messaggio «Metadato non trovato» (prima `search --id` dava il 404 grezzo). Il campo `id` del documento normalizzato resta il fileid.

# Examples

```bash
openrndt get "age:D_E973_MARSAGLIA"
openrndt get "age:D_E973_MARSAGLIA" --xml > metadato.xml
openrndt get agea:OI:ORTOIMMAGINI:m004 | jq -r .geolibre_map_url
```

# Comportamento ed errori

- ID inesistente → `ItemNotFoundError` → messaggio leggibile, exit 1 (l'API RNDT risponde 200 con `found: false`, non 404 — vedi [bug noti](/api/known-issues.md)).
- `--format csv` o `compact` → rifiutati con messaggio esplicito ed exit 1 **senza chiamata di rete**: il dettaglio non è tabellare; usare `json` (default) o `table`.
