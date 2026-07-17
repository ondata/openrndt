---
type: Project
title: openrndt
description: CLI e libreria Python read-only per interrogare il Repertorio Nazionale dei Dati Territoriali (RNDT).
resource: https://github.com/ondata/openrndt
tags: [rndt, geodati, cli, open-data, iso-19115]
timestamp: 2026-07-17T00:00:00Z
---

openrndt è una CLI Python (e libreria importabile) per cercare e recuperare metadati geografici dal [Repertorio Nazionale dei Dati Territoriali](https://geodati.gov.it/RNDT), il catalogo ufficiale italiano dei metadati geografici (ISO 19115/19139). È read-only: interroga l'API REST pubblica del RNDT, non scrive nulla.

# A chi serve

- **Umani da terminale**: ricerca dati territoriali (catasto, cartografia, uso del suolo, idrografia, …) con output `table` leggibile.
- **Agenti AI**: output JSON/NDJSON parsabile, errori sempre leggibili (mai stack trace), exit code distinti. La [skill rndt-explorer](/skill.md) guida l'esplorazione conversazionale.
- **Sviluppatori Python**: [API di libreria](/library/python-api.md) con eccezioni documentate.

# Principi di design

1. **Doppio uso CLI/libreria**: ogni funzionalità è esposta sia come comando sia come funzione importabile.
2. **Errori per orchestrazione LLM**: mai uno stack trace; messaggi self-contained su stderr; exit code 0 (ok), 1 (errore runtime/rete/not-found), 2 (parametri non validi). Vedi [gestione errori](/conventions/error-handling.md).
3. **Offline dove possibile**: le codelist ([discover](/cli/discover.md)) sono costanti Python, nessuna chiamata di rete.
4. **Verità verificata live, non doc ufficiale**: i comportamenti reali dell'API RNDT divergono dalla documentazione ufficiale; le divergenze sono catalogate in [bug noti](/api/known-issues.md).

# Stack

Python ≥ 3.12 gestito con `uv`. Dipendenze: `httpx` (HTTP), `typer` (CLI), `rich` (tabelle), `tenacity` (retry), `pydantic`. Test: `pytest` + `respx`, tutto mockato ([convenzioni di test](/conventions/testing.md)).

# Stato

Versione 1.0.0. Roadmap verso la produzione completata (valutazione originale in `docs/evaluation-v0.1.0.md`): `py.typed`, `mypy --strict`, CI GitHub Actions, metadata PyPI, installazione da PyPI documentata, `--timeout` configurabile, coverage 99%, `CHANGELOG.md`. Storico delle versioni in `CHANGELOG.md`.
