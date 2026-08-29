---
type: Agent Skill
title: rndt-explorer
description: Agent Skill che guida l'esplorazione conversazionale del catalogo RNDT tramite la CLI openrndt.
resource: skills/rndt-explorer/SKILL.md
tags: [skill, agenti, esplorazione]
timestamp: 2026-07-17T00:00:00Z
---

La skill `rndt-explorer` (in `skills/rndt-explorer/` nel repository) insegna a un agente AI a usare la [CLI](/cli/index.md) per trovare dati geografici italiani a partire da una domanda in linguaggio naturale — anche quando l'utente non nomina RNDT, geoportali o metadati.

# Le fasi

1. **Discovery (offline, sempre prima)** — [discover](/cli/discover.md) per conoscere codelist, parametri e campi Lucene senza rete.
2. **Ricerca progressiva** — [search](/cli/search.md) con filtri via via più stretti; `--format compact` per scremare molti risultati a basso costo di token.
3. **Dettaglio** — [get](/cli/get.md) sull'ID scelto; nel JSON i `links` puntano alle risorse fruibili.
4. **Fruizione** — segnalare all'utente le risorse scaricabili (WMS, WFS, download diretto); per l'ispezione dei servizi OGC la skill rimanda a GDAL/OGR con output JSON (`gdalinfo`/`ogrinfo -json`).
5. **Visualizzazione (opzionale)** — portare il dato trovato su una mappa [GeoLibre](https://geolibre.app), con la skill e il server MCP di quel progetto.

# Versionamento

`metadata.version` nel frontmatter è la versione **della skill**, e si
incrementa quando cambia il contenuto della skill, anche senza una release
della CLI: le due cose evolvono a ritmi diversi (una correzione a una reference
non tocca il codice). La versione minima di CLI richiesta si dichiara invece in
`compatibility`. Fino alla 3.1.0 i due numeri coincidevano perché la skill era
sempre cambiata insieme al codice.

# Riferimenti inclusi nella skill

| File | Contenuto |
|------|-----------|
| `references/categories.md` | Cheat sheet "bisogno → categoria ISO 19115". |
| `references/search-syntax.md` | Sintassi Lucene con esempi verificati. |
| `references/result-structure.md` | Struttura del JSON di risposta. |
| `references/output-formats.md` | Guida ai formati (vedi anche [la convenzione](/conventions/output-formats.md)). |
| `references/workflows.md` | Flussi tipici end-to-end, incluso il workflow per data journalist (dati scaricabili, licenza, citazione fonte). |
| `references/ogc-services.md` | Esplorazione WMS/WFS/WCS/WMTS con GDAL/OGR. |
| `references/csw.md` | Il catalogo come layer in QGIS/GDAL via CSW, con i limiti del servizio. |
| `references/geolibre.md` | Dal record RNDT a una mappa GeoLibre: nome del layer, https, pre-check GDAL, bounds, swipe, risorse inlineate. |
