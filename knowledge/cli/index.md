# Comandi CLI

* [search](search.md) - cerca metadati nel catalogo RNDT con filtri progressivi.
* [get](get.md) - dettaglio di un singolo metadato (JSON, XML ISO 19139, HTML).
* [discover](discover.md) - codelist e parametri validi, completamente offline.

# Opzioni globali

Le opzioni globali vanno **prima** del comando:

```bash
openrndt --format table search -q catasto
openrndt --base-url https://altro.esempio/RNDT search -q suolo
```

* `--format` / `-F` - formato di output: `json` (default), `table`, `csv`, `compact` (solo search). Vedi [formati di output](/conventions/output-formats.md).
* `--base-url` - override del base URL RNDT (in alternativa: env `OPENRNDT_BASE_URL`).
* `--timeout` - timeout HTTP in secondi per singolo tentativo (default 30s). Con i retry su timeout/5xx (3 tentativi) il caso peggiore è ~3x questo valore. Utile per un agente che non vuole aspettare a lungo su un host lento o irraggiungibile.
