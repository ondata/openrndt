# Knowledge Bundle — Update Log

## 2026-07-17

* **Update**: [project.md](/project.md) — versione 1.0.0, roadmap produzione completata (`CHANGELOG.md` nel repository).
* **Update**: [conventions/testing.md](/conventions/testing.md), [conventions/error-handling.md](/conventions/error-handling.md) — coverage 89%→99% (17 test nuovi, `tests/test_output.py`); bug reale trovato e corretto: `--format` invalido produceva un traceback, ora messaggio leggibile + exit 2.
* **Update**: [cli/index.md](/cli/index.md), [conventions/error-handling.md](/conventions/error-handling.md), [architecture.md](/architecture.md) — documentata la nuova opzione globale `--timeout` (stesso pattern di `--base-url`, override in `config.py`).
* **Update**: [conventions/testing.md](/conventions/testing.md) — aggiunta sezione CI: `.github/workflows/ci.yml` esegue ruff/mypy/pytest su push/PR, matrice Python 3.12/3.13.
* **Update**: [conventions/testing.md](/conventions/testing.md) estesa a "Testing e qualità statica": aggiunto `mypy --strict` (config in `pyproject.toml`), con le regole pratiche emerse (non propagare `Any` da `response.json()`, generics sempre parametrizzati, non riusare variabili con tipi diversi nello stesso scope).
* **Initialization**: creato il bundle OKF con la struttura iniziale: [project](/project.md), [architecture](/architecture.md), [skill](/skill.md), sezioni [cli/](/cli/index.md), [library/](/library/index.md), [api/](/api/index.md), [conventions/](/conventions/index.md).
