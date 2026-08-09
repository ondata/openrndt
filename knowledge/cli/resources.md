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
- Il check è un probe leggero: `HEAD`, con fallback a `GET` in streaming su **qualunque** `4xx`/`5xx`. I body non vengono mai scaricati. Il fallback serve perché molti WMS/WFS reali rifiutano `HEAD` con `403`/`405`/`500` pur rispondendo `200` a `GET`: il campo `method` dice quale richiesta ha prodotto il risultato finale.
- I redirect **non** vengono seguiti (evita che un record del catalogo faccia probare reti interne). Un `3xx` dà quindi `ok=false` — destinazione non verificata — con la Location riportata in `redirect_url`. `ok=true` significa risposta `2xx`.
- Vengono bloccati prima del probe gli URL con schema diverso da `http`/`https` e gli host che non sono indirizzi pubblici globalmente instradabili — per IP literal o per risoluzione DNS: loopback, link-local, private, reserved, multicast, unspecified e ogni altro range special-purpose (es. CGNAT `100.64.0.0/10`). Un hostname non risolvibile è bloccato anch'esso, perché non validabile. La riga riporta `error=url-blocked:<motivo>`.
