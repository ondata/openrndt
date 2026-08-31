# Valutazione della CLI openrndt 3.3.0

Data: 2026-08-31 · Commit valutato: `962c09e` (su `origin/main`, non ancora taggato) · Stato: non rilasciato (ultimo tag `v3.2.0`, PyPI a 3.2.0)

Nota: `docs/evaluation-v3.3.0.md` è un altro documento, la eval di triggering della descrizione della skill (skill 3.3.0, numerazione diversa da quella della CLI). Questo file valuta la CLI.

## Sintesi

La 3.3.0 fa una cosa sola e la fa bene: `get` smette di sputare la busta Elasticsearch e restituisce un documento con lo stesso vocabolario di `search`, più contatto, bbox, lineage e data del dato. Il codice nuovo è piccolo (156 righe effettive fra `search.py`, `resources.py`, `cli.py`), difensivo sui campi assenti, e coperto da test suoi. La suite è verde (156 test), ruff e mypy `strict` puliti, coverage 92%.

Il numero di versione è corretto, e l'ho verificato invece di dedurlo: confrontando `get --raw` e `get` sullo stesso record, le sette chiavi della busta (`_index`, `_id`, `_version`, `_seq_no`, `_primary_term`, `found`, `_source`) sono presenti con valori identici, e le sedici nuove si aggiungono senza collidere. Nessuna chiave rinominata, nessuna rimossa: la modifica è additiva, quindi minor e sotto *Added* è la collocazione giusta. Resta un difetto di comunicazione: la voce di changelog non dice che la busta è preservata, e chi legge «restituisce un documento normalizzato invece della busta Elasticsearch grezza» ha ragione di temere una rottura che non c'è.

Lo scarto vero è la parità CLI/libreria, che è una convenzione del progetto: 3.0.0 e 3.1.0 avevano esposto in `__init__.py` ogni helper nuovo (`record_dates`, `organization_names`, `compact_results`, `record_license`, `record_url`). La 3.3.0 non espone niente: `item_record`, `contact_point`, `download_urls`, `bbox_from_envelope` esistono solo dentro `openrndt.search`. E il README non è stato toccato: in 484 righe non compare né `--raw` né il documento normalizzato, e la sezione «Uso come libreria Python» insegna ancora `item["_source"]["title"]`.

## Punteggi per dimensione

| Dimensione | Voto | Nota |
|---|---|---|
| Progettazione della feature | 9/10 | il documento normalizzato è la forma giusta; `--raw` è la via d'uscita corretta |
| Qualità del codice nuovo | 8/10 | difensivo e leggibile; due nei di forma, un URL hardcoded |
| Test | 8/10 | ogni campo nuovo ha il suo test; manca il caso `--raw` con `--xml` |
| Documentazione interna (skill, knowledge) | 9/10 | `result-structure.md` e `knowledge/cli/get.md` allineati e verificati |
| Documentazione utente (README) | 4/10 | non aggiornata per nulla della 3.3.0 |
| Versionamento e release | 8/10 | numerazione corretta (modifica additiva, verificata); changelog reticente sulla compatibilità |

## Verifiche fatte

Tutte con `uv run` (il binario del venv è 3.3.0, verificato con `--version`), contro l'API viva.

- Additività della modifica a `get`: `get --raw` contro `get` sullo stesso record, confronto chiave per chiave delle sette della busta - nessuna differisce per valore. Le sedici nuove si aggiungono e basta.
- Suite: 156 test verdi, `ruff check` pulito, `mypy --strict` pulito, coverage 92% (cli.py 86%, resources.py 89%, search.py 99%).
- Contratto documentato contro output reale, su `c_l219:a883ab12-…` (WMS catasto urbano, Comune di Torino): le 16 chiavi del documento normalizzato coincidono una a una con la tabella di `references/result-structure.md`, e in coda ci sono i sette campi della busta (`_index`, `_id`, `_version`, `_seq_no`, `_primary_term`, `found`, `_source`). L'affermazione del changelog - «il contratto documentato di `get` coincide ora con l'output reale» - è vera.
- Permalink costruito da `item_record` uguale a quello che `record_url` estrae dai link `alternate` per lo stesso record, encoding dei due punti compreso (`c_l219%3A…`).
- `resources_nst` con precedenza: sul record di Torino la risorsa `resources_nst` (https, con tipo dal catalogo) precede quella di `links_s` (http, tipo dedotto), e la dedup per URL non le fonde perché gli indirizzi differiscono nello schema.
- Campione di 300 record dal catalogo: 228 hanno `resources_nst`; **nessuno** ha `resources_nst` senza avere anche link corrispondenti, e per **nessuno** l'insieme dei tipi ricavati da `resources_nst` differisce da quello ricavato da `links`. L'asimmetria fra `get` (che legge `resources_nst`) e `compact` (che legge ancora `links`) è quindi documentale, non sostanziale.
- Campi ad arità variabile: su 300 record, `apiso_Lineage_txt` è un array in 263 casi, ma **sempre di un solo elemento**; `title`, `description`, `fileid`, `PuntoDiContatto*`, `apiso_Type_s`, `apiso_OrganizationName_txt` sono sempre scalari. La scelta di `_first_str` (prendi il primo, scarta il resto) non perde nulla di misurabile su questo campione.
- `PuntoDiContattoEmail_s` è sempre stringa sui 300 record: la normalizzazione a lista in `download_urls` serve invece davvero, perché `url_download_s` e `url_http_download_s` arrivano scalari o array a seconda della scheda.

## Rilievi

### 1. Il changelog non dice che la modifica è additiva (bassa)

La voce recita «`get` con `--format json` (default) restituisce un documento normalizzato **invece della** busta Elasticsearch grezza», e in coda «`_source` e i flag della busta restano inalterati». La prima frase spaventa, la seconda rassicura, e chi si ferma alla prima non aggiorna. Verificato che la seconda è quella vera: le sette chiavi della busta escono identiche fra `get --raw` e `get`. Basta una riga in testa alla voce - «la modifica è additiva: nessuna chiave preesistente cambia nome o valore» - perché il lettore capisca che non deve migrare nulla.

### 2. Parità CLI/libreria non rispettata (media)

`src/openrndt/__init__.py:16` elenca in `__all__` gli helper delle release precedenti ma nessuno dei quattro nuovi. Chi usa openrndt come libreria non ha modo di ottenere il documento normalizzato se non importando da `openrndt.search`, un modulo privato per convenzione. Da esportare: `item_record`, `contact_point`, `download_urls`, `bbox_from_envelope`.

### 3. README fermo alla 3.2.0 (media)

Nessuna occorrenza di `--raw`, «normalizzato», `contact`, `data_date`. La sezione «Uso come libreria Python» (riga 387) mostra `item = get_item(...)` seguito da `item["_source"]["title"]`, che resta valido ma non è più il modo consigliato. `knowledge/cli/get.md` e la reference della skill sono invece aggiornate: la documentazione per agenti ha avuto la cura che è mancata a quella per umani.

### 4. Permalink hardcoded, sordo al base URL configurato (bassa)

`search.py:376` fissa `CATALOG_PERMALINK = "https://geodati.gov.it/geoportal-catalog/rest/metadata/item"`, mentre tutto il resto della libreria passa da `config.set_base_url` / `OPENRNDT_BASE_URL`. Su un mirror il documento normalizzato continuerebbe a citare geodati.gov.it. L'impatto reale è minimo, perché l'host del permalink non coincide comunque con quello dell'API, ma il commento in codice («lo stesso che il server mette nei link `alternate`») descrive un fatto verificato per il portale ufficiale e non per un mirror: converrebbe dirlo.

### 5. `--raw` ignorato in silenzio con `--xml` e `--html` (bassa)

`cli.py:712` fa fallire `--xml --html` insieme con un messaggio esplicito, ma `--raw --xml` passa e `--raw` viene semplicemente ignorato. Delle due combinazioni non sensate, una avvisa e l'altra no. Coerenza da poco prezzo: un `BadParameter` anche lì.

### 6. Due nei di forma, e un cancello di lint più stretto di quanto sembri (bassa)

`search.py:449` ha uno spazio in coda dentro il docstring di `compact_results`, e a `search.py:484` ci sono tre righe vuote prima di `organization_names`. Nessuno dei due è colpa di una svista di revisione: `ruff check` passa perché la configurazione non seleziona regole e quindi resta al set di default (`E4`, `E7`, `E9`, `F`), che non contiene `W291`. Con `--select W,I` ruff trova entrambi più un import non ordinato. Vale la pena scegliere consapevolmente il set di regole in `pyproject.toml`, così che «ruff pulito» voglia dire qualcosa di più.

### 7. Campi del documento non elencati nel changelog (bassa)

La voce di changelog elenca id, title, org, type, category, date, `data_date`, `contact`, `bbox`, `lineage`, `resources`, `url`. Il documento reale contiene anche `description`, `open` e `license`: sono coperti dalla formula «stessi campi delle risposte di `search`», ma `description` in `compact` non c'è, quindi lì la formula non lo copre.

## Cosa fare prima di rilasciare

1. Esportare i quattro helper in `__init__.py`. → verifica: `python -c "from openrndt import item_record, contact_point, download_urls, bbox_from_envelope"`.
2. Aggiornare il README: `--raw` nella sezione uso, il documento normalizzato negli esempi, `item_record` nella sezione libreria. → verifica: `grep -c "\-\-raw" README.md` maggiore di zero.
3. Alzare `compatibility` della skill a `>= 3.3.0` e correggere i sette punti elencati sotto. → verifica: nessuna occorrenza di `_source.links_s` come via consigliata per `get`.
4. Aggiungere alla voce di changelog la riga sull'additività. → verifica: la voce dice esplicitamente che nessuna chiave preesistente cambia.
5. `BadParameter` per `--raw` con `--xml`/`--html`, con test. → verifica: nuovo test in `tests/test_cli.py`, suite verde.
6. Ripulire i due nei e decidere il set di regole ruff. → verifica: `ruff check --select E,W,F,I` pulito.

## Esito

Tutti i punti di «Cosa fare prima di rilasciare» sono stati chiusi il 2026-08-31, skill compresa (passata alla 3.4.0). Dettaglio in `tasks/todo.md` e in `LOG.md`.

## Domande aperte

- `compact` deve leggere `resources_nst` come fa `get`? Sul campione non cambierebbe un solo record: forse basta dichiarare nel docstring che le due strade convergono, e rimandare.
- Il permalink va costruito dal base URL configurato o resta ancorato al portale ufficiale?

## Allineamento della skill `rndt-explorer` alla 3.3.0

La skill è allineata dove la 3.3.0 l'ha toccata di proposito, e ferma alla 3.2.0 dove il commit non è passato. Il commit `962c09e` ha modificato `SKILL.md` e `references/result-structure.md`, lasciando intatte le altre cinque reference: è lì che stanno i disallineamenti.

Allineato:

- `SKILL.md:47-54`: la lista dei campi di `compact` include `email` e `download`, con la nota sulla loro origine.
- `references/result-structure.md:153-182`: il documento normalizzato di `get` è documentato campo per campo e `--raw` è spiegato. Verificato contro l'output reale: coincide.

Non allineato:

1. **`compatibility` dichiara `openrndt >= 3.1.0`** (`SKILL.md:21`), ma la skill ora insegna `--raw` e il documento normalizzato, che esistono dalla 3.3.0. Un agente su una CLI 3.1.0 che segue la reference riceve `No such option: --raw`. Da alzare a `>= 3.3.0` (o alla versione con cui si rilascerà).
2. **`SKILL.md:204`** descrive ancora `openrndt --format json get <id>` come «JSON Elasticsearch (`_source` completo)»: è la riga che l'agente legge in Fase 3, ed è falsa dalla 3.3.0. Stessa frase in `references/result-structure.md:49`.
3. **Fase 4, `SKILL.md:235-237`**: «I servizi e i file scaricabili stanno in `results[].links[]` … o in `_source.links_s` / `_source.webServices_s` (per `get`)». Dalla 3.3.0 `get` li espone in `.resources`, già tipizzati e deduplicati, con `resources_nst` in testa. La strada vecchia funziona ancora (`_source` è preservato) ma è la lunga.
4. **`SKILL.md:54`** e **`references/output-formats.md:41`**: «se `resources` è `[]` fai `get <id>` e guarda `_source.links_s`» → ora `.resources` di `get` è la risposta diretta.
5. **`references/output-formats.md:28-32`**: la lista dei campi di `compact` non è stata aggiornata, mancano `email` e `download`. È l'unico punto in cui la stessa informazione è scritta due volte e le due copie divergono.
6. **`references/workflows.md:29`**: `jq -r '._source.links_s[]?'` → `jq -r '.resources[].url'`.
7. **`references/workflows.md:207-209`**: l'esempio «licenza, ente e data per la citazione» ricostruisce a mano da `._source.isOpendata`, `._source.EnteResponsabile_s`, `._source.apiso_Modified_dt` esattamente i tre campi che la 3.3.0 mette al primo livello come `.open`/`.license`, `.org`, `.updated`. È l'esempio che la nuova feature rende inutile, ed è rimasto.

Nessuno di questi rompe qualcosa: `_source` è preservato, quindi ogni `jq` della skill continua a dare lo stesso risultato. Il costo è di altro tipo - la skill insegna la via lunga per una cosa che ora la CLI fa da sola, e il punto 1 può far fallire un comando su un'installazione non aggiornata.
