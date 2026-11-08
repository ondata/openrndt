# Knowledge Bundle — Update Log

## 2026-11-08

* **Update**: [cli/search.md](/cli/search.md), [cli/footprints.md](/cli/footprints.md), [cli/discover.md](/cli/discover.md), [library/python-api.md](/library/python-api.md) — `--inspire-theme`, `--inspire-cluster`, `discover --what inspire_themes`, `inspire_tree`.
* **Update**: [api/known-issues.md](/api/known-issues.md) — valori di `INSPIRETheme_s` e Requisito 1.4.

## 2026-11-01

* **Update**: [cli/get.md](/cli/get.md) — `geolibre_map_url`, `--no-map-link`, id e fileid.
* **Update**: [cli/resources.md](/cli/resources.md) — WMTS in `--layers`: griglia Web Mercator, template, CORS, campi `kind`/`tile_url`/`cors`.
* **Update**: [library/python-api.md](/library/python-api.md) — `geolibre_map_url`, funzioni WMTS, `catalog_ids_for_fileid`.
* **Update**: [api/known-issues.md](/api/known-issues.md) — `_id` diverso dal fileid e tipo di servizio dichiarato diverso dall'URL (AGEA).

## 2026-07-17

* **Update**: [api/known-issues.md](/api/known-issues.md), [skill.md](/skill.md) — audit live della skill rndt-explorer: il sort su `title` ora funziona (API cambiata), `dateDescending` riconfermato rotto; skill aggiornata (workflow corretti, campo `apiso_PublicationDate_dt` inesistente rimosso, formato compact documentato, nuovo workflow data journalist).
* **Update**: [project.md](/project.md) — versione 1.0.0, roadmap produzione completata (`CHANGELOG.md` nel repository).
* **Update**: [conventions/testing.md](/conventions/testing.md), [conventions/error-handling.md](/conventions/error-handling.md) — coverage 89%→99% (17 test nuovi, `tests/test_output.py`); bug reale trovato e corretto: `--format` invalido produceva un traceback, ora messaggio leggibile + exit 2.
* **Update**: [cli/index.md](/cli/index.md), [conventions/error-handling.md](/conventions/error-handling.md), [architecture.md](/architecture.md) — documentata la nuova opzione globale `--timeout` (stesso pattern di `--base-url`, override in `config.py`).
* **Update**: [conventions/testing.md](/conventions/testing.md) — aggiunta sezione CI: `.github/workflows/ci.yml` esegue ruff/mypy/pytest su push/PR, matrice Python 3.12/3.13.
* **Update**: [conventions/testing.md](/conventions/testing.md) estesa a "Testing e qualità statica": aggiunto `mypy --strict` (config in `pyproject.toml`), con le regole pratiche emerse (non propagare `Any` da `response.json()`, generics sempre parametrizzati, non riusare variabili con tipi diversi nello stesso scope).
* **Initialization**: creato il bundle OKF con la struttura iniziale: [project](/project.md), [architecture](/architecture.md), [skill](/skill.md), sezioni [cli/](/cli/index.md), [library/](/library/index.md), [api/](/api/index.md), [conventions/](/conventions/index.md).
