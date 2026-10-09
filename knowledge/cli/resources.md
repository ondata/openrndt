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
| `--layers` | Legge le GetCapabilities di ogni WMS e aggiunge `layers`: un elemento per layer con nome, con `geolibre_url` che apre GeoLibre web con quel layer già sulla mappa. Sostituisce `--check` (le capabilities dicono già se il servizio risponde). In `table`/`csv` le righe sono i layer. |

# Layer (`--layers`)

Ogni elemento di `layers` ha `service` (base del WMS), `name`, `title`, `crs`, `geolibre_url`, `note`, `error`. Il link usa `rndtLayer=<id>~wms~<nome>` del plugin openrndt-geolibre (dalla 0.3.5, issue #30). Le regole ricalcano quelle del plugin, perché un link che il plugin non sa seguire fallirebbe senza avvisi:

- Un servizio per base URL, nell'ordine della scheda: si tolgono solo i parametri di operazione (`SERVICE`, `REQUEST`, `LAYERS`, …), `?map=` di MapServer resta, e `http`/`https` dello stesso indirizzo contano una volta.
- `crs` è il sistema in cui GeoLibre web chiederebbe il layer: EPSG:3857 se c'è, altrimenti uno geografico (4326, 4258, 6706, CRS:84 solo in 1.3.0), altrimenti il primo `EPSG:n`. Senza nessuno di questi `geolibre_url` è `null`, con una nota.
- Un nome già visto in un servizio precedente della scheda ha `geolibre_url` `null`: il plugin usa il primo servizio che lo elenca.
- Se la scheda dichiara lo stesso servizio in `http://` e in `https://` si usa `https://`. Un servizio solo in `http://` ha il link, con una nota: su web.geolibre.app (https) il browser può non mostrarlo. Il CORS non si controlla.
- GeoServer pubblica lo stesso workspace a `…/ows` e a `…/wms`: se la scheda li elenca entrambi sono due servizi, e i layer del secondo risultano «nome già in un servizio precedente» con `geolibre_url` `null`. Non sono layer inutilizzabili: il link del primo servizio vale per tutti e due.
- Un servizio che non risponde, o risponde con un'eccezione OGC o XML non valido, dà una riga con `name` `null` ed `error`.
- Le capabilities si scaricano con le stesse protezioni di `--check` (host non pubblici bloccati, anche dopo un redirect), fino a 10 MB.
- Solo WMS: le immagini ArcGIS REST (`~arcgis~`) non sono ancora coperte (#33).

# Examples

```bash
# Estrazione + verifica endpoint (default)
openrndt resources age:D_E973_MARSAGLIA

# Solo estrazione URL, senza check HTTP
openrndt resources age:D_E973_MARSAGLIA --no-check

# Layer dei WMS, ognuno con il suo geolibre_url
openrndt resources r_emiro:2022-03-11T113115 --layers | jq -r '.layers[] | "\(.name)\t\(.geolibre_url)"'
```

# Comportamento ed errori

- Formati supportati: `json` (default), `table`, `csv`, `compact`.
- ID inesistente → messaggio leggibile, exit 1.
- Errori di rete nei check delle singole risorse non interrompono il comando: la riga è marcata con `ok=false` e campo `error`.
- Il check è un probe leggero: `HEAD`, con fallback a `GET` in streaming su **qualunque** `4xx`/`5xx`. I body non vengono mai scaricati. Il fallback serve perché molti WMS/WFS reali rifiutano `HEAD` con `403`/`405`/`500` pur rispondendo `200` a `GET`: il campo `method` dice quale richiesta ha prodotto il risultato finale.
- I redirect vengono seguiti fino a 3, solo se ogni destinazione supera la stessa validazione dell'URL iniziale (evita che un record del catalogo faccia probare reti interne): un `3xx` verso un host non pubblico si ferma con `error=redirect-blocked:<motivo>`. Se c'è stato un redirect la riga riporta `redirected`, `redirect_count` e `redirect_url` (prima destinazione). `ok=true` significa risposta finale `2xx`.
- Vengono bloccati prima del probe gli URL con schema diverso da `http`/`https` e gli host che non sono indirizzi pubblici globalmente instradabili — per IP literal o per risoluzione DNS: loopback, link-local, private, reserved, multicast, unspecified e ogni altro range special-purpose (es. CGNAT `100.64.0.0/10`). Un hostname non risolvibile è bloccato anch'esso, perché non validabile. La riga riporta `error=url-blocked:<motivo>`.
