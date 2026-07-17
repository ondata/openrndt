---
type: CLI Command
title: openrndt discover
description: Espone le codelist e i parametri validi del RNDT, completamente offline.
tags: [cli, discover, codelist, offline]
timestamp: 2026-07-17T00:00:00Z
---

Nessuna chiamata di rete: le codelist sono costanti Python in `codelists.py`. È il punto di partenza consigliato per un agente ([skill, Fase 1](/skill.md)).

# Sezioni disponibili (`--what`)

| Sezione | Contenuto |
|---------|-----------|
| `all` (default) | Tutte le sezioni seguenti. |
| `data_categories` | Le 19 categorie ISO 19115 TopicCategoryCode (es. `planningCadastre`, `environment`) con descrizione italiana. |
| `sort_values` | Valori di ordinamento **verificati live**, inclusi i valori ufficiali che non funzionano. |
| `output_formats` | Formati del parametro `f` dell'API (`json`, `atom`, `csw`, `csv`, `kml`, …). |
| `search_params` | Parametri dell'endpoint search con note d'uso. |
| `lucene_fields` | Campi Elasticsearch interrogabili in `--q`, con suffissi (`_txt`, `_s`, `_dt`, `_i`, `_b`) e regole wildcard. |

# Examples

```bash
openrndt discover                                # tutto, JSON
openrndt discover --what data_categories
openrndt --format table discover --what lucene_fields
```

Sezione sconosciuta → `BadParameter` con l'elenco delle sezioni disponibili, exit 2.
