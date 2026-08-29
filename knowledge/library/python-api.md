---
type: Python API
title: API pubblica della libreria openrndt
description: Funzioni ed eccezioni esportate da `import openrndt` per uso programmatico.
tags: [libreria, python, api]
timestamp: 2026-07-17T00:00:00Z
---

Tutto ciò che la [CLI](/cli/index.md) fa è disponibile anche come libreria. Export pubblici (`openrndt.__all__`): `search`, `compact_results`, `record_dates`, `record_license`, `record_url`, `organization_names`, `get_item`, `get_item_xml`, `get_item_html`, `ItemNotFoundError`, `main`, `__version__`.

# Schema

| Simbolo | Firma / significato |
|---------|---------------------|
| `search(*, q, bbox, bbox_crs, org, org_exact, data_category, time, modified, updated_from, updated_to, published_from, published_to, sort, start=1, num=10, fmt="json", item_id=None)` | Ricerca su `/rest/metadata/search`. Ritorna `dict` se `fmt` è `json`/`json-source`, altrimenti `str` col body grezzo (XML, CSV, KML, …). |
| `get_item(item_id)` | `dict` Elasticsearch del metadato (`_source` + flag). |
| `get_item_xml(item_id)` | `str` XML ISO 19139. |
| `get_item_html(item_id)` | `str` HTML. |
| `ItemNotFoundError` | Sollevata da `get_item` se l'ID non esiste; espone `.item_id`. |
| `record_dates(result)` | In `openrndt.search`: tupla `(updated, indexed)` di un singolo risultato — `apiso_Modified_dt` e `sys_modified_dt`. |
| `organization_names(payload)` | In `openrndt.search`: nomi di ente distinti nei risultati, ordinati per frequenza. L'API ignora `facet`: è l'unico modo di scoprire come un ente è scritto in catalogo. |
| `record_license(source)` | In `openrndt.search`: tupla `(open, license)` dal campo `isOpendata` di `_source`. `open` è la presenza del campo, `license` i valori diversi dai marcatori `opendata`/`open data`, non normalizzati. |
| `record_url(result)` | In `openrndt.search`: permalink della scheda sul portale (link `rel="alternate"`, `type="text/html"`), `None` se assente. |
| `compact_results(payload)` | In `openrndt.search`: riduce il payload di `search()` a record sintetici (`id`, `title`, `org`, `type`, `category`, `updated` = `apiso_Modified_dt`, `indexed` = `sys_modified_dt`, `open`, `license`, `url`, `resources`). |

# Eccezioni propagate

- `ValueError` — parametri non validi (`num` > 5000, `start` < 1, `org` e `org_exact` insieme, date non ISO, `bbox` malformata: quattro valori numerici, longitudini in -180..180, latitudini in -90..90, `xmin < xmax`, `ymin < ymax`).
- `httpx.HTTPError` — include `httpx.HTTPStatusError` (risposte 4xx/5xx) e `httpx.ConnectError`/`httpx.TimeoutException` (rete).
- `json.JSONDecodeError` (sottoclasse di `ValueError`) — risposta 2xx con body non-JSON.
- `ItemNotFoundError` — solo da `get_item`.

# Examples

```python
import openrndt

payload = openrndt.search(q="uso del suolo", data_category="environment", num=5)
for r in payload["results"]:
    print(r["id"], r["title"])

# Cosa pubblica un ente, con le date separate
payload = openrndt.search(org="comune di torino", num=20)
for rec in openrndt.compact_results(payload):
    print(rec["updated"], rec["indexed"], rec["title"])

try:
    item = openrndt.get_item("age:D_E973_MARSAGLIA")
except openrndt.ItemNotFoundError as exc:
    print(f"non trovato: {exc.item_id}")
```

# Limiti noti

Il base URL è stato globale di modulo (`openrndt.config.set_base_url()` / env `OPENRNDT_BASE_URL`): non thread-safe con base URL diversi in parallelo. Vedi [architettura](/architecture.md).
