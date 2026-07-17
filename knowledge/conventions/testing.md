---
type: Convention
title: Testing e qualità statica
description: Suite pytest interamente offline (respx), lint ruff, type-checking mypy strict.
tags: [test, pytest, respx, mypy, ruff]
timestamp: 2026-07-17T00:00:00Z
---

Regola fissa: **nessuna chiamata di rete nei test**. Tutto l'HTTP è mockato con `respx`; le fixture JSON reali sono in `tests/fixtures/`.

# Esecuzione

```bash
uv run pytest                                          # 55 test
uv run pytest --cov=openrndt --cov-report=term-missing # coverage (99%)
uv run ruff check .                                    # lint
uv run mypy src/openrndt                               # type-checking strict
```

# Type-checking (mypy strict)

`[tool.mypy]` in `pyproject.toml` ha `strict = true`. Regole pratiche emerse nel farlo passare pulito:

- **`response.json()` di httpx ritorna `Any`**: annotare esplicitamente la variabile che lo riceve (es. `data: dict[str, Any] = response.json()`) per non propagare `Any` — che disattiva i controlli — nella catena di chiamate a valle. Vedi `search.py`, `item.py`.
- **`dict`/`list` senza parametri generici** sono errore in strict: sempre `dict[str, Any]`, mai `dict` nudo.
- **Non riusare una variabile con due tipi diversi** nello stesso scope (mypy inferisce il tipo dalla prima assegnazione): è anche un campanello di leggibilità, non solo un vincolo del type checker.

# CI

`.github/workflows/ci.yml` esegue automaticamente su push/PR verso `main`, matrice Python 3.12/3.13: `uv sync --locked` (fallisce se `uv.lock` non è aggiornato) → `ruff check` → `mypy` → `pytest -v`. Nessun deploy/pubblicazione automatica: solo verifica.

# Cosa coprono i test

| File | Copertura |
|------|-----------|
| `test_search.py` | Costruzione query (clausola `keywords_s`, combinazioni q+categoria), validazione parametri, `compact_results` (org/category/resources con fallback). |
| `test_item.py` | get JSON/XML/HTML, `found: false` → `ItemNotFoundError`, encoding ID. |
| `test_retry.py` | Retry: 503×3 → errore, 503→200 → successo; connessione rifiutata. |
| `test_cli.py` | Exit code e messaggi: no-traceback su errori di rete, JSON malformato con status 200, formati incrociati, `get --format csv` rifiutato, 0 risultati. |
| `test_discover.py` | Codelist offline, sezioni, `--what` sconosciuto. |
| `test_output.py` | Rami di `output.py` irraggiungibili dalla CLI (tabella senza righe, CSV vuoto): testati chiamando `output.emit()` direttamente, non tramite `CliRunner`. |

# Gap noti

99% di coverage; l'unica parte scoperta è il boilerplate d'ingresso `main()`/`if __name__ == "__main__"` in `cli.py`, basso valore.

# Una lezione dal chiudere i gap

Cercare la copertura mancante ha fatto emergere un bug reale, non solo righe scoperte: `--format <valore-invalido>` produceva un traceback completo, perché `output.set_mode()` solleva `ValueError` che nessuno catturava nel callback root di `cli.py` — violava il principio "mai uno stack trace" di [gestione errori](/conventions/error-handling.md). Nessun test copriva quel percorso, quindi nessuno se n'era accorto. Morale: un gap di coverage sui percorsi di errore/parametri è spesso un bug non ancora scoperto, non solo un numero da migliorare.
