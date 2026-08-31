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

`--xml` e `--html` sono mutuamente esclusivi, e `--raw` non si combina con nessuno dei due (riguarda solo l'output JSON). Con `--format json` (default) dalla 3.3.0 `get` restituisce il **documento normalizzato**: gli stessi campi delle risposte di `search` più email di contatto, bbox, lineage e data del dato (schema in [result-structure.md](/skill/rndt-explorer/references/result-structure.md)); `_source` è preservato per chi lo usa. `--raw` ripristina la busta Elasticsearch completa, vista che contiene i `links` alle risorse fruibili (WMS, WFS, download diretto).

# Examples

```bash
openrndt get "age:D_E973_MARSAGLIA"
openrndt get "age:D_E973_MARSAGLIA" --xml > metadato.xml
```

# Comportamento ed errori

- ID inesistente → `ItemNotFoundError` → messaggio leggibile, exit 1 (l'API RNDT risponde 200 con `found: false`, non 404 — vedi [bug noti](/api/known-issues.md)).
- `--format csv` o `compact` → rifiutati con messaggio esplicito ed exit 1 **senza chiamata di rete**: il dettaglio non è tabellare; usare `json` (default) o `table`.
