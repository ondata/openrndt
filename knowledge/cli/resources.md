---
type: CLI Command
title: openrndt resources
description: Estrae endpoint WMS/WFS/download da un metadato RNDT e ne verifica la raggiungibilità HTTP.
tags: [cli, resources, ogc]
timestamp: 2026-08-09T00:00:00Z
---

Recupera il metadato con [get](/cli/get.md), estrae le risorse fruibili dai campi `links`, `_source.links_s`, `_source.webServices_s` e opzionalmente testa ogni URL con una richiesta HTTP.

# Opzioni

| Opzione | Significato |
|---------|-------------|
| `ITEM_ID` (argomento) | ID del metadato (es. `age:D_E973_MARSAGLIA`). |
| `--check/--no-check` | Verifica (default `--check`) o salta (`--no-check`) il test HTTP degli endpoint estratti. |

# Examples

```bash
# Estrazione + verifica endpoint (default)
openrndt resources age:D_E973_MARSAGLIA

# Solo estrazione URL, senza check HTTP
openrndt resources age:D_E973_MARSAGLIA --no-check
```

# Comportamento ed errori

- Formati supportati: `json` (default), `table`, `csv`, `compact`.
- ID inesistente → messaggio leggibile, exit 1.
- Errori di rete nei check delle singole risorse non interrompono il comando: la riga è marcata con `ok=false` e campo `error`.
