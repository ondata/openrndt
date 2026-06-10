# Formati di output

`openrndt` ha due livelli di formato:

1. **Formato del comando CLI** (`--format` globale): `json` (default), `table`, `csv`.
   Controlla come la CLI stampa il risultato.
2. **Formato della risposta API** (`-f` interno, gestito automaticamente):
   `json`, `atom`, `csv`, `kml`, ecc. Non esposto direttamente nella CLI MVP —
   tutte le ricerche chiedono `json` all'API per garantire parsing affidabile.

## Quando usare ciascun formato CLI

| Scenario                                          | Formato consigliato |
|---------------------------------------------------|---------------------|
| Pipeline `\| jq`, scripting Python/Bash            | `json` (default)    |
| Mostrare risultati in chat all'utente             | `table`             |
| Esportare in foglio di calcolo                     | `csv`               |
| Recuperare XML ISO 19139 per validatori INSPIRE   | `openrndt get <id> --xml` |
| Generare pagina HTML del metadato                  | `openrndt get <id> --html` |

## Esempi

```bash
# JSON puro su stdout, errori su stderr
openrndt --format json search --q catasto > out.json

# Tabella Rich con colonne id/title/updated/author/bbox
openrndt --format table search --q catasto --num 10

# CSV con header
openrndt --format csv search --q catasto --num 50 > catasto.csv

# XML ISO 19139 di un singolo metadato
openrndt get age:D_E973_MARSAGLIA --xml > meta.xml
xmllint --noout meta.xml && echo "XML valido"
```

## Convenzioni di output JSON

- Solo `stdout` viene popolato con JSON; `stderr` resta per errori.
- Nessun banner, nessun spinner, nessuna formattazione human-readable.
- La struttura rispecchia 1:1 la response RNDT
  (`/rest/metadata/search` o `/rest/metadata/item/{id}`).
