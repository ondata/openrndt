# openrndt

CLI Python e libreria per accedere al **Repertorio Nazionale dei Dati Territoriali (RNDT)** —
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

## Uso come libreria Python

```python
from openrndt import search, get_item, get_item_xml, ItemNotFoundError

# Ricerca
results = search(q="catasto", num=5)
for r in results["results"]:
    print(r["id"], r["title"])

# Filtro per categoria e bbox
results = search(data_category="planningCadastre", bbox="7,44,8,45", num=10)

# Dettaglio singolo metadato
item = get_item("age:D_E973_MARSAGLIA")
print(item["_source"]["title"])

# XML ISO 19139
xml = get_item_xml("age:D_E973_MARSAGLIA")

# Gestione ID inesistente
try:
    item = get_item("id_inesistente")
except ItemNotFoundError:
    print("metadato non trovato")
```

Le funzioni propagano le eccezioni `httpx`: `httpx.HTTPStatusError` per le
risposte 4xx/5xx e `httpx.ConnectError` / `httpx.TimeoutException` (dopo i
retry) per i problemi di rete. Tutte derivano da `httpx.HTTPError`, comodo per
catturarle insieme:

```python
import httpx
from openrndt import search

try:
    results = search(q="catasto")
except httpx.HTTPError as exc:
    print(f"richiesta fallita: {exc}")
```

Il base URL è configurabile via variabile d'ambiente o parametro:

```python
from openrndt.config import set_base_url
set_base_url("https://mio-mirror.example.com/RNDT")
```

## Per agenti AI

L'utente primario di questa CLI è un agente che legge `stdout` e compone i comandi
passo passo. Da qui i principi di design (sul modello di
[opensdmx](https://github.com/aborruso/opensdmx)):

- **Output strutturato, mai oggetti Python.** Default JSON su `stdout`; `--format
  table` per la lettura umana, `--format csv` per i risultati tabellari.
- **In modalità JSON, `stdout` contiene solo JSON.** Errori e avvisi vanno su
  `stderr`: si può fare pipe diretta in `jq`.
- **Errori leggibili e self-contained: mai stack trace.** Un errore di rete o HTTP
  produce un messaggio comprensibile su `stderr` ed exit code `1`, non un traceback.
- **Exit code chiari.** `0` successo, `1` errore (rete, HTTP, ID inesistente),
  `2` parametri non validi.
- **Niente formati ambigui.** `get <id> --format csv` (dettaglio non tabellare)
  fallisce con un messaggio esplicito invece di restituire output vuoto.

Il progetto include inoltre una skill Claude Code in `skills/rndt-explorer/` che guida
un agente attraverso le 4 fasi: scoperta delle codelist, ricerca con filtri progressivi,
lettura del dettaglio, download delle risorse collegate (WMS/WFS/download).

## Riferimenti

- Pagina ufficiale REST API: <https://geodati.gov.it/geoportale/eng/strumenti-en/rest-api>
- Spec completa (sito di test Esri Geoportal Server, non produzione): <https://gpt.geocloud.com/geoportal3/api/gpt_api.json>
- Documentazione raccolta nella cartella [`ref/`](./ref).

## Licenza

MIT.
