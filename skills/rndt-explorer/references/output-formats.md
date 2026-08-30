# Formati di output

`openrndt` ha due livelli di formato:

1. **Formato del comando CLI** (`--format` globale): `json` (default), `table`,
   `csv`, `compact` (NDJSON, solo per `search`).
   Controlla come la CLI stampa il risultato.
   Eccezione: `search --profile ...` senza `--format` esplicito passa da solo a
   `table`; con `--format json`/`compact` espliciti il preset non si applica e
   la CLI avvisa su stderr.
2. **Formato della risposta API** (`-f` interno, gestito automaticamente):
   `json`, `atom`, `csv`, `kml`, ecc. Non esposto direttamente nella CLI MVP —
   tutte le ricerche chiedono `json` all'API per garantire parsing affidabile.

## Quando usare ciascun formato CLI

| Scenario                                          | Formato consigliato |
|---------------------------------------------------|---------------------|
| Pipeline `\| jq`, scripting Python/Bash            | `json` (default)    |
| Scremare molti risultati a basso costo di token (agenti) | `compact`     |
| Mostrare risultati in chat all'utente             | `table` (`--profile gis` consigliato) |
| Esportare in foglio di calcolo / QGIS             | `csv` (`--profile qgis`) |
| Recuperare XML ISO 19139 per validatori INSPIRE   | `openrndt get <id> --xml` |
| Generare pagina HTML del metadato                  | `openrndt get <id> --html` |
| Estrarre/check endpoint servizi del record         | `openrndt resources <id>` |
| Portare footprint bbox in GIS                      | `openrndt footprints ... > file.geojson` |

## `compact` — NDJSON per agenti (solo `search`)

Una riga JSON per record con i soli campi ad alto segnale: `id`, `title`,
`org`, `type`, `category`, `updated` (data della scheda, `apiso_Modified_dt`),
`indexed` (indicizzazione nel catalogo, `sys_modified_dt`), `open`, `license`,
`url`, `resources`.

```bash
openrndt --format compact search --q "frane AND isOpendata:*" --num 30
```

- `resources` elenca i tipi di servizio/download fruibili (`WMS`, `WFS`,
  `download`, …). Se è `[]` il record non linka servizi: per i dettagli fai
  `get <id>` e guarda `_source.links_s`.
- `open` e `license` vengono da `isOpendata`, non normalizzato: `license` può
  essere `CC BY 4.0` come un intero paragrafo di disclaimer, e `open=false`
  significa «l'ente non l'ha dichiarato lì», non «dato chiuso» (alcune schede
  aperte hanno la licenza solo in `apiso_OtherConstraints_s`).
- `url` è il permalink della scheda sul portale: usalo per citare la fonte.
- In `--format table` `url` non viene stampata, `open` esce come `sì`/`no` e
  `license` è troncata a 60 caratteri; in `csv` e `compact` i valori sono interi.
- `get --format compact` (come `csv`) è rifiutato: il dettaglio non è tabellare.

## Esempi

```bash
# JSON puro su stdout, errori su stderr
openrndt --format json search --q catasto > out.json

# Tabella Rich con colonne id/title/updated/org/author/open/license/bbox (indexed e url solo nei profili gis/qgis e in compact/csv)
openrndt --format table search --q catasto --num 10

# Tabella "GIS-friendly" (il profilo implica già --format table)
openrndt search --q catasto --profile gis --num 10

# CSV con header
openrndt --format csv search --q catasto --num 50 > catasto.csv

# CSV "QGIS-ready" con URL servizi + xmin/ymin/xmax/ymax
openrndt --format csv search --q catasto --profile qgis --num 50 > catasto_qgis.csv

# Estrazione + check endpoint WMS/WFS/download
openrndt resources age:D_E973_MARSAGLIA

# Footprint bbox come poligoni GeoJSON
openrndt footprints --q catasto --num 100 > footprints.geojson

# XML ISO 19139 di un singolo metadato
openrndt get age:D_E973_MARSAGLIA --xml > meta.xml
xmllint --noout meta.xml && echo "XML valido"
```

## Convenzioni di output JSON

- Solo `stdout` viene popolato con JSON; `stderr` resta per errori.
- Nessun banner, nessun spinner, nessuna formattazione human-readable.
- La struttura rispecchia 1:1 la response RNDT
  (`/rest/metadata/search` o `/rest/metadata/item/{id}`).
