# openrndt

CLI Python per accedere al **Repertorio Nazionale dei Dati Territoriali (RNDT)** —
pensata per essere orchestrata da un'AI.

> Stato: alpha (v0.1) — read-only.

## Cos'è il RNDT

Il [Repertorio Nazionale dei Dati Territoriali](https://geodati.gov.it/geoportale/) è
il catalogo ufficiale italiano dei metadati geografici (ISO 19115/19139). Espone REST
API per cercare e scaricare i metadati.

## Installazione

```bash
# CLI globale (consigliato): venv isolato, eseguibile in PATH
uv tool install /path/to/openrndt

# Aggiornamento dopo modifiche al codice
uv tool install --reinstall /path/to/openrndt

# Disinstallazione
uv tool uninstall openrndt
```

Per sviluppo (modifiche con ricarica immediata):

```bash
git clone <repo>
cd openrndt
uv sync
uv run openrndt --help
```

## Uso

```bash
# Ricerca testuale
openrndt search --q "catasto" --num 5

# Filtro per bounding box (Piemonte sud)
openrndt search --q "cartografia" --bbox 7,44,8,45 --num 10

# Per categoria tematica ISO 19115
openrndt search --data-category planningCadastre --num 5

# Singolo metadato
openrndt get age:D_E973_MARSAGLIA

# XML ISO 19139 grezzo
openrndt get age:D_E973_MARSAGLIA --xml > meta.xml

# Codelist disponibili (no rete)
openrndt discover
```

Tutti i comandi accettano `--format json` (default), `--format table`, `--format csv`.

## Per agenti AI

Il progetto include una skill Claude Code in `skills/rndt-explorer/` che guida un
agente attraverso le 4 fasi: scoperta delle codelist, ricerca con filtri progressivi,
lettura del dettaglio, download delle risorse collegate (WMS/WFS/download).

## Riferimenti

- Pagina ufficiale REST API: <https://geodati.gov.it/geoportale/eng/strumenti-en/rest-api>
- Spec completa (sito di test Esri Geoportal Server, non produzione): <https://gpt.geocloud.com/geoportal3/api/gpt_api.json>
- Documentazione raccolta nella cartella [`ref/`](./ref).

## Licenza

MIT.
