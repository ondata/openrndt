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
| `ipa` | Vocabolario dei codici IPA presenti nel RNDT (non è in `all`): codice, se è nell'Indice PA, nome e acronimo IPA, categoria IPA (`categoria`, `nome_categoria`: `L6`, «Comuni e loro Consorzi e Associazioni»), nomi in `EnteResponsabile_s`, schede, grafie del prefisso. Con `--match <testo>` solo i codici il cui codice, nome, acronimo o ente lo contiene (`--match arpae` → `arpa`); la categoria non entra nella ricerca. Se il vocabolario non trova nulla, `--match` cerca nell'anagrafica dell'Indice PA nel pacchetto (`data/ipa-enti.csv.gz`, 23.757 enti, 397 KB) e restituisce, con un avviso su stderr, gli enti senza schede nel RNDT: stessa forma, `schede: 0`, `enti` e `grafie` vuoti (#44). `--match "comune di palermo"` → `c_g273`; `palermo` → 41 enti, prima le categorie che pubblicano più schede nel RNDT (Comune e Città metropolitana prima di scuole e ordini). In JSON `{"generato", "codici"}`. Vocabolario e anagrafica li scrive `scripts/build_ipa_vocabulary.py` prima di ogni release. |

# Examples

```bash
openrndt discover                                # tutto, JSON
openrndt discover --what data_categories
openrndt --format table discover --what lucene_fields
openrndt --format table discover --what ipa --match veneto
```

Sezione sconosciuta → `BadParameter` con l'elenco delle sezioni disponibili, exit 2.
