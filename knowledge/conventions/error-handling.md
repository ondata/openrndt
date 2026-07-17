---
type: Convention
title: Gestione errori
description: Principi e mappa completa di exit code e messaggi d'errore della CLI.
tags: [errori, exit-code, llm-friendly]
timestamp: 2026-07-17T00:00:00Z
---

Principio: un agente che orchestra la CLI deve capire l'esito dal solo output. Mai uno stack trace; messaggi self-contained (includono sempre l'URL o il valore problematico) su **stderr**; stdout resta pulito per i dati.

# Mappa exit code

| Exit | Caso | Messaggio (stderr) |
|------|------|--------------------|
| 0 | Successo; include ricerca con 0 risultati (con avviso "Nessun risultato per la ricerca."). | — |
| 1 | Errore HTTP (status) | `Errore HTTP {status}: {url}` |
| 1 | Errore di rete (connessione, DNS, timeout dopo i retry) | `Errore di rete: impossibile contattare {url} ({TipoEccezione}).` |
| 1 | ID inesistente in [get](/cli/get.md) | `Metadato non trovato: {id}` |
| 1 | Risposta 2xx con body non-JSON | `Risposta RNDT inattesa (JSON non valido).` |
| 1 | `get --format csv\|compact` (dettaglio non tabellare) — rifiutato senza chiamata di rete | messaggio esplicito che suggerisce json o table |
| 2 | Parametri non validi (`--num` > 5000, `--start` < 1, `--format` non supportato, `--what` sconosciuto, `--xml`+`--html` insieme) | messaggio con valore e limite |

# Retry e timeout

`client.py` ritenta 3 volte con backoff esponenziale (max 10 s) su `httpx.TimeoutException` e risposte 5xx. Non ritenta su `ConnectError` (fallisce subito). Il timeout per singolo tentativo è configurabile con `--timeout` (default 30 s, vedi [opzioni globali](/cli/index.md)): con i retry, il caso peggiore resta ~3x il valore impostato.

# Nella libreria

La [libreria](/library/python-api.md) non converte: propaga le eccezioni tipizzate (`ValueError`, `httpx.HTTPError`, `json.JSONDecodeError`, `ItemNotFoundError`) documentate nelle docstring; è la CLI a tradurle in messaggi ed exit code.
