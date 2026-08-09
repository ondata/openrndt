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
| `sort=dateDescending` / `dateAscending` ordinano per data. | Ignorati: ordine identico fra loro (riconfermato 2026-07-17). | `discover --what sort_values` marca i valori rotti; la sintassi funzionante è `campo:asc\|desc` su campo sortable (es. `apiso_Modified_dt:desc`). |
| — | Ordinare su un campo `text` analizzato (es. `title` nudo) dava errore Elasticsearch "Fielddata is disabled"; **dal 2026-07-17 risulta funzionare** (`title:asc` ordina alfabeticamente — comportamento API cambiato). | Documentato nelle codelist; i campi garantiti sortable restano `_s`/`_dt`/`_i`. |
| Esiste una data di pubblicazione ordinabile. | `apiso_PublicationDate_dt` **esiste** (8.402/23.632 record ~36%) ed è **filtrabile** via `q=apiso_PublicationDate_dt:[range]`, ma **non ordinabile** (`sort=…` ignorato, come `apiso_RevisionDate_dt`). Verificato live 2026-07-17 — corregge la nota precedente che lo dava per "inesistente". `apiso_CreationDate_dt` spesso null/parziale. | Proxy per "più recenti": `apiso_Modified_dt:desc`. Per *filtrare* (non ordinare) per data di pubblicazione: `q=apiso_PublicationDate_dt:[…]` (issue #4). |
| Il filtro per data della Ricerca Dettagliata rispetta il tipo di data scelto. | Mette in AND tutti e 3 i campi data; i record privi di uno di essi sono scartati anche con "Considera valori vuoti" spuntato. Es. "incendi creati dal 2024": 15 reali, portale 0. | Bug del frontend ufficiale, non della CLI (issue #9). |
| L'endpoint CSW supporta `SortBy` (INSPIRE Discovery Services v3.1). | `SortBy` ignorato: non conforme. | Nessuna: documentato (issue #5 del repository). |
| Item inesistente → errore HTTP. | Risponde `200` con body `{"found": false}`. | `get_item` controlla `found` e solleva `ItemNotFoundError`. |

# Problemi di qualità dei dati (non dell'API)

- Alcuni record dichiarano una bbox errata che copre tutta l'Italia (`6.6,35.5,18.5,47.1`): compaiono come rumore in qualunque ricerca `--bbox`. Il filtro bbox in sé funziona (semantica overlaps, verificata).

# Citations

[1] `ref/rest-api-rndt.md` e `LOG.md` nel repository (verifiche live datate).
[2] [Pagina ufficiale REST API RNDT](https://geodati.gov.it/geoportale/eng/strumenti-en/rest-api)
