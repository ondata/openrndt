# Workflow tipici

Sequenze pronte da copiare. Tutte testate live su
`https://geodati.gov.it/RNDT` (numeri reali al 2026-05-27 in coda).

## 1. Catasto in provincia (filtro tematico + spaziale)

> "Trova i dataset catastali della provincia di Cuneo (bbox indicativa
> 7.0,44.0,8.5,45.0)."

```bash
# 1. categoria giusta (offline)
openrndt --format json discover --what data_categories | jq '.planningCadastre'
#   → "Pianificazione e catasto"

# 2. ricerca
openrndt --format json search \
  --q "catasto" \
  --data-category planningCadastre \
  --bbox 7.0,44.0,8.5,45.0 \
  --num 20

# 3. dettaglio del primo risultato
ID=$(openrndt --format json search --q "catasto" --data-category planningCadastre \
      --bbox 7.0,44.0,8.5,45.0 --num 1 | jq -r '.results[0].id')
openrndt --format json get "$ID" | jq '._source | {title, contact_organizations_s, INSPIRETheme_s}'

# 4. risorse scaricabili
openrndt --format json get "$ID" | jq -r '._source.links_s[]?'
```

## 2. Tutti i WMS di un tema INSPIRE

> "Lista degli endpoint WMS pubblicati nel RNDT per il tema INSPIRE
> Idrografia."

```bash
openrndt --format json search \
  --q 'INSPIRETheme_s:Idrografia' \
  --num 500 \
  | jq -r '.results[].links[]?
            | select(.dctype=="WMS") | .href' \
  | sort -u > wms-idrografia.txt
```

## 3. Cosa pubblica un ente specifico

> "Quali dataset risultano pubblicati dall'Agenzia delle Entrate?"

```bash
openrndt --format table search \
  --q 'contact_organizations_s:"Agenzia delle Entrate"' \
  --num 20 --sort dateDescending
```

## 4. Aggiornamenti recenti

> "Dataset modificati nel 2024, dal più recente."

```bash
openrndt --format json search \
  --time "2024-01-01/2024-12-31" \
  --sort dateDescending \
  --num 30
```

> ⚠️ **Limiti API noti**:
> 1. `--time` combinato con `--data-category` (o con qualsiasi `--q` su un
>    campo specifico tipo `keywords_s:…`) restituisce 0 risultati.
> 2. Il campo top-level `updated` di ogni risultato riflette la data di
>    reindicizzazione del catalogo (uguale per tutti), non la data del dataset.
>    Per ordinare/filtrare per "data del dataset" usare i campi `_source`:
>    - `apiso_RevisionDate_dt` — data di revisione del metadato
>    - `apiso_CreationDate_dt` — data di creazione del metadato
>    - `apiso_PublicationDate_dt` — data di pubblicazione
>    - `timeperiod_nst[].begin_dt`/`end_dt` — copertura temporale dei dati
>      (è il campo su cui agisce il parametro `--time`)
>
> Workaround per "inlandWaters revisionati nel 2024":
>
> ```bash
> openrndt --format json search --data-category inlandWaters --num 500 \
>   | jq '[.results[] | select(._source.apiso_RevisionDate_dt
>           and ._source.apiso_RevisionDate_dt >= "2024-01-01"
>           and ._source.apiso_RevisionDate_dt <  "2025-01-01")] | length'
> ```

## 5. Scarica l'XML ISO 19139 di un metadato

```bash
openrndt get age:D_E973_MARSAGLIA --xml > meta.xml
xmllint --noout meta.xml && echo "XML valido"
```

## 6. CSV per fogli di calcolo

```bash
openrndt --format csv search --q "ortofoto" --num 100 > ortofoto.csv
```

## Risultati di riferimento (sanity check)

Numeri ottenuti live al 2026-05-27 — utili per accorgersi di regressioni:

| Query                                                              | `total` atteso |
|--------------------------------------------------------------------|---------------:|
| `--q "catasto"`                                                    | 8.814          |
| `--data-category planningCadastre`                                 | 11.351         |
| `--data-category "planningCadastre,boundaries"`                    | 11.720         |
| `--q 'INSPIRETheme_s:Idrografia'`                                  | 845            |
| `--q 'contact_organizations_s:"Agenzia delle Entrate"'`            | 7.699          |
| catalogo completo (`--q "*"` o nessun filtro)                      | 23.580         |
