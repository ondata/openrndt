---
type: External API
title: API REST del RNDT
description: Gli endpoint del geoportale RNDT usati da openrndt e i campi Lucene interrogabili.
resource: https://geodati.gov.it/RNDT
tags: [rndt, rest, elasticsearch, lucene]
timestamp: 2026-07-17T00:00:00Z
---

Il RNDT espone un'API REST in stile Esri Geoportal Server su base `https://geodati.gov.it/RNDT` (configurabile via env `OPENRNDT_BASE_URL`). È read-only e senza autenticazione. openrndt applica retry esponenziale (3 tentativi) su timeout e 5xx.

# Endpoint usati

| Endpoint | Uso in openrndt |
|----------|-----------------|
| `GET /rest/metadata/search` | [search](/cli/search.md). Parametri: `q` (Lucene), `bbox`, `time`, `modified`, `sort`, `start`, `num` (max 5000), `f` (formato), `id`. |
| `GET /rest/metadata/item/{id}` | [get](/cli/get.md), JSON Elasticsearch. |
| `GET /rest/metadata/item/{id}/xml` | XML ISO 19139. |
| `GET /rest/metadata/item/{id}/html` | HTML. |

# Campi Lucene principali (parametro `q`)

L'elenco completo con descrizioni è offline in [discover --what lucene_fields](/cli/discover.md). Regole sui suffissi:

| Suffisso | Tipo | Note |
|----------|------|------|
| `_txt` | testo analizzato | wildcard trailing OK (`palerm*`), leading non supportata su campo esplicito. |
| `_s` | keyword, case-sensitive | wildcard solo trailing. |
| `_dt` | data ISO 8601 | range `[2024-01-01T00:00:00Z TO *]`; sortable. |
| `_i` | intero | range `[1 TO 10000]`. |
| `_b` | booleano | `true` \| `false`. |

Campi ad alto valore: `apiso_Type_s` (dataset/series/service), `apiso_TopicCategory_s`, `apiso_OrganizationName_txt`, `apiso_Modified_dt`, `isOpendata` (`isOpendata:*` per tutti gli open data), `apiso_Format_s`, `INSPIRETheme_s`, `AmbitoTerritoriale_s`.

Molti comportamenti reali divergono dalla documentazione ufficiale: vedi [bug noti](/api/known-issues.md).

# Citations

[1] [Pagina ufficiale REST API RNDT](https://geodati.gov.it/geoportale/eng/strumenti-en/rest-api)
[2] [Spec Esri Geoportal Server](https://gpt.geocloud.com/geoportal3/api/gpt_api.json)
[3] Mirror locale della documentazione: `ref/rest-api-rndt.md` nel repository.
