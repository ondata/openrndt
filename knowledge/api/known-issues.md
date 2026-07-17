---
type: Reference
title: Bug noti dell'API RNDT
description: Divergenze verificate live tra la documentazione ufficiale RNDT e il comportamento reale dell'API.
tags: [rndt, bug, verificato-live]
timestamp: 2026-07-17T00:00:00Z
---

Tutti i punti seguenti sono stati verificati empiricamente contro l'API di produzione, non dedotti dalla documentazione. openrndt li compensa dove possibile.

# Divergenze

| Comportamento documentato | Comportamento reale | Compensazione in openrndt |
|---------------------------|---------------------|---------------------------|
| Il parametro `dataCategory` filtra per categoria. | Non filtra: ritorna sempre il catalogo intero. | `--data-category` è tradotto nella clausola Lucene `q=keywords_s:VAL` (`OR` per valori multipli). |
| `sort=dateDescending` / `dateAscending` ordinano per data. | Ignorati: ordine identico fra loro. | `discover --what sort_values` marca i valori rotti; la sintassi funzionante è `campo:asc\|desc` su campo sortable (es. `apiso_Modified_dt:desc`). |
| — | Ordinare su un campo `text` analizzato (es. `title` nudo) dà errore Elasticsearch "Fielddata is disabled". | Documentato nelle codelist; usare i campi `_s`/`_dt`/`_i`. |
| Esiste una data di pubblicazione ordinabile. | Non esiste; `apiso_CreationDate_dt` è spesso null o fittizia (es. 2012-01-01). | Proxy consigliato per "più recenti": `apiso_Modified_dt:desc` (issue #4 del repository). |
| L'endpoint CSW supporta `SortBy` (INSPIRE Discovery Services v3.1). | `SortBy` ignorato: non conforme. | Nessuna: documentato (issue #5 del repository). |
| Item inesistente → errore HTTP. | Risponde `200` con body `{"found": false}`. | `get_item` controlla `found` e solleva `ItemNotFoundError`. |

# Problemi di qualità dei dati (non dell'API)

- Alcuni record dichiarano una bbox errata che copre tutta l'Italia (`6.6,35.5,18.5,47.1`): compaiono come rumore in qualunque ricerca `--bbox`. Il filtro bbox in sé funziona (semantica overlaps, verificata).

# Citations

[1] `ref/rest-api-rndt.md` e `LOG.md` nel repository (verifiche live datate).
[2] [Pagina ufficiale REST API RNDT](https://geodati.gov.it/geoportale/eng/strumenti-en/rest-api)
