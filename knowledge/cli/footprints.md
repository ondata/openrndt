---
type: CLI Command
title: openrndt footprints
description: Esporta le bbox dei risultati RNDT in GeoJSON FeatureCollection (EPSG:4326).
tags: [cli, geojson, qgis]
timestamp: 2026-08-09T00:00:00Z
---

Esegue una ricerca come [search](/cli/search.md) e converte ogni `results[].bbox` in un poligono GeoJSON.

# Opzioni

Le opzioni di filtro sono allineate a `search` (`--q`, `--bbox`, `--bbox-crs`, `--org`, `--org-exact`, `--data-category`, `--time`, `--modified`, `--updated-from`, `--updated-to`, `--published-from`, `--published-to`, `--sort`, `--start`, `--num`).

# Examples

```bash
# Footprint dei risultati su "catasto"
openrndt footprints --q "catasto" --num 50 > footprints.geojson

# Footprint filtrati per bbox e aggiornamento
openrndt footprints \
  --bbox 11.2,44.4,11.5,44.6 \
  --updated-from 2024-01-01 \
  --num 100 > bologna_2024.geojson
```

# Output

- `type: FeatureCollection`
- `crs: EPSG:4326`
- `features[]`: poligono bbox + proprietà essenziali (`id`, `title`, `org`, `type`, `updated` = data della scheda, `indexed` = indicizzazione nel catalogo, `resources`)
- `meta`: contatori utili (`total_results`, `features_with_bbox`, `start`, `num`)
