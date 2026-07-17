---
type: Agent Skill
title: rndt-explorer
description: Agent Skill che guida l'esplorazione conversazionale del catalogo RNDT tramite la CLI openrndt.
resource: skills/rndt-explorer/SKILL.md
tags: [skill, agenti, esplorazione]
timestamp: 2026-07-17T00:00:00Z
---

La skill `rndt-explorer` (in `skills/rndt-explorer/` nel repository) insegna a un agente AI a usare la [CLI](/cli/index.md) per trovare dati geografici italiani a partire da una domanda in linguaggio naturale — anche quando l'utente non nomina RNDT, geoportali o metadati.

# Le quattro fasi

1. **Discovery (offline, sempre prima)** — [discover](/cli/discover.md) per conoscere codelist, parametri e campi Lucene senza rete.
2. **Ricerca progressiva** — [search](/cli/search.md) con filtri via via più stretti; `--format compact` per scremare molti risultati a basso costo di token.
3. **Dettaglio** — [get](/cli/get.md) sull'ID scelto; nel JSON i `links` puntano alle risorse fruibili.
4. **Fruizione** — segnalare all'utente le risorse scaricabili (WMS, WFS, download diretto); per l'ispezione dei servizi OGC la skill rimanda a GDAL/OGR con output JSON (`gdalinfo`/`ogrinfo -json`).

# Riferimenti inclusi nella skill

| File | Contenuto |
|------|-----------|
| `references/categories.md` | Cheat sheet "bisogno → categoria ISO 19115". |
| `references/search-syntax.md` | Sintassi Lucene con esempi verificati. |
| `references/result-structure.md` | Struttura del JSON di risposta. |
| `references/output-formats.md` | Guida ai formati (vedi anche [la convenzione](/conventions/output-formats.md)). |
| `references/workflows.md` | Flussi tipici end-to-end. |
| `references/ogc-services.md` | Esplorazione WMS/WFS/WCS/WMTS con GDAL/OGR. |
