---
type: Python API
title: API pubblica della libreria openrndt
description: Funzioni ed eccezioni esportate da `import openrndt` per uso programmatico.
tags: [libreria, python, api]
timestamp: 2026-07-17T00:00:00Z
---

Tutto ciò che la [CLI](/cli/index.md) fa è disponibile anche come libreria. Export pubblici (`openrndt.__all__`): `search`, `get_item`, `get_item_xml`, `get_item_html`, `ItemNotFoundError`, `main`, `__version__`.

# Schema

| Simbolo | Firma / significato |
|---------|---------------------|
| `search(*, q, bbox, data_category, time, modified, sort, start=1, num=10, fmt="json", item_id=None)` | Ricerca su `/rest/metadata/search`. Ritorna `dict` se `fmt` è `json`/`json-source`, altrimenti `str` col body grezzo (XML, CSV, KML, …). |
| `get_item(item_id)` | `dict` Elasticsearch del metadato (`_source` + flag). |
| `get_item_xml(item_id)` | `str` XML ISO 19139. |
| `get_item_html(item_id)` | `str` HTML. |
| `ItemNotFoundError` | Sollevata da `get_item` se l'ID non esiste; espone `.item_id`. |
| `compact_results(payload)` | In `openrndt.search`: riduce il payload di `search()` a record sintetici (`id`, `title`, `org`, `type`, `category`, `updated`, `resources`). |

# Eccezioni propagate

- `ValueError` — parametri non validi (`num` > 5000, `start` < 1).
- `httpx.HTTPError` — include `httpx.HTTPStatusError` (risposte 4xx/5xx) e `httpx.ConnectError`/`httpx.TimeoutException` (rete).
- `json.JSONDecodeError` (sottoclasse di `ValueError`) — risposta 2xx con body non-JSON.
- `ItemNotFoundError` — solo da `get_item`.

# Examples

```python
import openrndt

payload = openrndt.search(q="uso del suolo", data_category="environment", num=5)
for r in payload["results"]:
    print(r["id"], r["title"])

try:
    item = openrndt.get_item("age:D_E973_MARSAGLIA")
except openrndt.ItemNotFoundError as exc:
    print(f"non trovato: {exc.item_id}")
```

# Limiti noti

Il base URL è stato globale di modulo (`openrndt.config.set_base_url()` / env `OPENRNDT_BASE_URL`): non thread-safe con base URL diversi in parallelo. Vedi [architettura](/architecture.md).
