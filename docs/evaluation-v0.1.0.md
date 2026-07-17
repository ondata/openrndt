# Valutazione openrndt v0.1.0 — readiness per produzione

Data: 2026-07-17. Metodologia: lettura sistematica di `src/openrndt/` (7 moduli, 299 statement), esecuzione reale della suite test (`uv run pytest` + coverage con `pytest-cov`), build effettiva del package (`uv build` + `twine check`), esecuzione CLI live contro `https://geodati.gov.it/RNDT` (search reale, 8.827 risultati per "catasto"), test di percorsi d'errore (ID inesistente, parametro fuori range, host irraggiungibile, formato non tabellare). Valutazione indipendente, senza riferimenti a valutazioni precedenti.

## Giudizio sintetico

Il codice è solido, coerente e già production-grade nella sua logica applicativa: gestione errori disciplinata, test reali (non mock banali), doc allineata al comportamento verificato live. Quello che manca per una release pubblica non è nel codice ma nell'infrastruttura attorno: non c'è CI, non c'è type-checking automatizzato, il packaging PyPI ha lacune di metadata (repo non linkato, licenza in formato deprecato), e non esiste un blocco netto — è un progetto a un passo dalla v1.0, non a metà strada.

## Punti di forza

- **Gestione errori disegnata per agenti AI, verificata empiricamente**: mai uno stack trace, exit code distinti (0/1/2), messaggi su stderr. Confermato dai test live: ID inesistente → `exit 1` con messaggio leggibile; `--num 99999` → `exit 2`; `get --format csv` → rifiutato con messaggio esplicito senza chiamata di rete.
- **Suite test reale**: 38 test, 89% coverage (`pytest --cov`), tutti mockati via `respx` (nessuna rete), copre retry (503×3 vs 503→200), JSON malformato con status 200, connessione rifiutata, formati di output incrociati.
- **Documentazione insolitamente onesta e verificata sul campo**: `LOG.md` e `codelists.py` documentano bug reali dell'API RNDT scoperti live (`dataCategory` non filtra, `sort` "amichevole" ignorato, CSW non conforme INSPIRE) — non copiati dalla doc ufficiale ma testati.
- **Doppio uso CLI/libreria reale**, non solo dichiarato: `from openrndt import search, get_item, ItemNotFoundError` funziona, eccezioni documentate nelle docstring, README ha sezione libreria dedicata con esempi.
- **Build PyPI funzionante**: `uv build` produce wheel+sdist validi, `twine check` passa senza errori.
- **Superficie di sicurezza minima e correttamente gestita**: `_encode_id()` usa `quote(safe="")`, i parametri passano per l'encoding httpx, l'API è read-only e il passthrough Lucene in `--q` è una feature intenzionale (documentata), non un vettore di injection.

## Gap per la produzione

### IMPORTANTE

1. **Nessuna CI/CD** (`.github/` assente). Ogni merge si affida a run manuali locali. Fix: workflow GitHub Actions minimo — `uv sync && uv run pytest && uv run ruff check .` su push/PR, matrice 3.12/3.13.
2. **Metadata PyPI incompleti per un consumo di terzi** — `pyproject.toml:33-35`: `[project.urls]` punta solo al portale dati e alla pagina REST API; mancano `Repository`/`Issues`/`Changelog` verso `https://github.com/ondata/openrndt`. Fix: aggiungere `Repository` e `Issues`, mantenendo il link RNDT con etichetta chiara (es. `"RNDT Portal"`).
3. **README con installazione solo locale** — `README.md:16-25`: `uv tool install /path/to/openrndt` presuppone un clone locale. Fix: aggiungere sezione "da PyPI" quando pubblicato, tenendo quella locale come "per sviluppo".
4. **Nessun type-checking automatizzato**: `mypy`/`pyright` non installati né in `[dependency-groups].dev` (`pyproject.toml:37-43`). Il codice usa type hints ovunque ma nessuno li valida. Fix: aggiungere `mypy` (o `pyright`) al gruppo dev + step CI.
5. **Timeout di rete potenzialmente lungo per un agente che orchestra la CLI** — `client.py:16,25-29`: `DEFAULT_TIMEOUT=30.0` + retry 3× con `wait_exponential(max=10)` su `TimeoutException` può far attendere fino a ~90 secondi prima di un errore leggibile su un host lento/irraggiungibile (verificato empiricamente). Nessun flag CLI per abbassare timeout/retry. Fix: esporre `--timeout` (il parametro esiste già nella funzione, manca solo il flag CLI) e/o ridurre il default per la CLI interattiva.
6. **Manca `py.typed`** (PEP 561): assente sia in `src/openrndt/` che nel wheel buildato. Per un package pensato anche come libreria, i tipi non sono distribuiti a chi lo importa. Fix: aggiungere file vuoto `src/openrndt/py.typed` e verificarne la presenza nel wheel al prossimo build.
7. **Nessun CHANGELOG** separato da `LOG.md`. `LOG.md` è un diario di sviluppo, non un changelog utile a chi aggiorna la versione. Fix: `CHANGELOG.md` in formato Keep-a-Changelog, popolato almeno al primo tag di release.

### NICE-TO-HAVE

8. **Stato globale mutabile in `config.py` e `output.py`** (`config.py:10,19-21`; `output.py:14,18-22`): `_override` e `_output_mode` sono variabili modulo-livello. Irrilevante per la CLI; race condition latente per uso libreria in contesto concorrente. Da documentare come limite.
9. **Nessun client HTTP condiviso**: `client.py:32` apre una nuova connessione a ogni chiamata (niente keep-alive/pooling). Trascurabile per la CLI, penalizzante per molte chiamate in sequenza da libreria.
10. **Licenza in formato deprecato da PEP 639** — `pyproject.toml:9`: `license = { text = "MIT" }` è la forma legacy; la raccomandata è `license = "MIT"` (stringa SPDX). Fix banale.
11. **Versione duplicata**: `__version__` in `__init__.py:7` e `version` in `pyproject.toml:3` da tenere sincronizzate a mano. Fix: derivare l'una dall'altra (es. `importlib.metadata.version()`).
12. **Copertura test non uniforme**: `output.py` al 71% (branch `table` senza `table_rows`, rami `csv` vuoti); `cli.py` all'87% (`search --format compact` con 0 risultati, `discover` non-json per sezione singola, `main()`). Nessun percorso critico, ma vale la pena chiudere prima di v1.0.
13. **`ref/` e `PRD.md` senza indice**: utili per chi sviluppa, non arrivano al consumatore PyPI (correttamente esclusi dal wheel).

## Roadmap consigliata verso v1.0

1. Aggiungere `py.typed`, verificare la sua presenza nel wheel dopo build.
2. Aggiungere `mypy` (o `pyright`) al gruppo dev, far passare pulito.
3. Creare `.github/workflows/ci.yml`: `uv sync`, `pytest`, `ruff check`, matrice 3.12/3.13.
4. Sistemare `[project.urls]`: aggiungere `Repository`/`Issues`, chiarire il link RNDT come portale dati.
5. Aggiornare README con installazione da PyPI accanto a quella locale per sviluppo.
6. Esporre `--timeout`/retry configurabili in CLI.
7. Chiudere i gap di coverage residui in `output.py`/`cli.py`.
8. Aggiungere `CHANGELOG.md`, taggare `v1.0.0`, pubblicare su PyPI (`uv build` + `uv publish`).
9. Facoltativo: migrare la licenza alla forma stringa SPDX; automatizzare `__version__` da un'unica fonte.
