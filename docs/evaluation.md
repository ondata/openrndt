# Valutazione progetto openrndt

Data: 2026-06-10 · Versione progetto: 0.1.0 (alpha)

## Sintesi

MVP solido e coerente: 3 comandi CLI funzionanti, architettura snella (547 LOC
sorgente, 7 moduli a responsabilità singola), convenzioni di CLAUDE.md tutte
rispettate. Un test fallisce per assertion non aggiornata; una dipendenza
dichiarata (`pydantic`) non è usata; la gestione errori HTTP non arriva
all'utente con messaggi leggibili.

## Punteggi per dimensione

| Dimensione | Voto |
|---|---|
| Architettura / modularità | 9/10 |
| Qualità codice | 7/10 |
| Test | 6/10 |
| Documentazione | 9/10 |
| Configurazione progetto | 7/10 |
| Conformità convenzioni | 9/10 |

## Punti di forza

- Architettura a strati piatta: CLI → dominio → HTTP → config. Nessun ciclo.
- `codelists.py` come costanti pure: `discover` funziona offline.
- Bug API `dataCategory` documentato su 3 livelli (CLAUDE.md, ref/, SKILL.md),
  testato e risolto automaticamente (`search.py:_build_category_clause`).
- Skill `rndt-explorer` completa (SKILL.md + 5 reference verticali).
- Fixture di test reali (JSON/XML del RNDT), non costruite a mano.
- Base URL configurabile su 3 livelli (default, env, flag), testata.

## Problemi (per severità)

### Alta
1. **Test fallente** — `tests/test_discover.py:21`: l'assertion non include
   `"lucene_fields"`, aggiunto dopo in `codelists.py`. `1 failed, 18 passed`.
2. **`pydantic` non usato** — `pyproject.toml:28`: dichiarato in `dependencies`
   ma mai importato. Rimuovere oppure usarlo per modellare le risposte.
3. **Errori HTTP non gestiti** — i 4xx propagano `httpx.HTTPStatusError` fino al
   top-level: l'utente vede un traceback invece di un messaggio (`openrndt get
   inesistente`).

### Media
4. **Variabile morta `last_exc`** — `client.py:25` (ruff F841).
5. **`assert isinstance` in produzione** — `cli.py:94`: eliminato con `python -O`.
   Usare un check esplicito con `raise typer.Exit`.
6. **Retry non testato** — zero test su 5xx/retry/4xx, il componente più critico
   per la robustezza.
7. **Stato globale `_output_mode`** — non resettato esplicitamente in conftest
   (rischio latente di contaminazione tra test).

### Bassa
8. `--format` non validato presenta traceback invece di errore CLI leggibile.
9. Parametro `modified` non verificato nei test di `search.py`.
10. `LOG.md` con un'unica entry molto densa.

## Raccomandazioni prioritizzate

1. Fix `tests/test_discover.py:21` aggiungendo `"lucene_fields"` al set atteso.
2. Rimuovere `pydantic` da `pyproject.toml` (o adottarlo per i modelli).
3. Wrappare le chiamate HTTP in `cli.py` con `try/except httpx.HTTPStatusError`
   per messaggi utente leggibili.
4. Rimuovere `last_exc` da `client.py:25`.
5. Aggiungere test retry: 503→200 e 3×503→fallimento.
6. Reset `output.set_mode("json")` come fixture autouse in conftest.
