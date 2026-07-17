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

`--xml` e `--html` sono mutuamente esclusivi. Il JSON di default è il documento Elasticsearch del metadato (`_source` + flag), la vista più ricca: contiene i `links` alle risorse fruibili (WMS, WFS, download diretto).

# Examples

```bash
openrndt get "age:D_E973_MARSAGLIA"
openrndt get "age:D_E973_MARSAGLIA" --xml > metadato.xml
```

# Comportamento ed errori

- ID inesistente → `ItemNotFoundError` → messaggio leggibile, exit 1 (l'API RNDT risponde 200 con `found: false`, non 404 — vedi [bug noti](/api/known-issues.md)).
- `--format csv` o `compact` → rifiutati con messaggio esplicito ed exit 1 **senza chiamata di rete**: il dettaglio non è tabellare; usare `json` (default) o `table`.
