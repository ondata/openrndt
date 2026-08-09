# Idee future

Spunti raccolti per evoluzioni di openrndt. Non sono impegni: vanno valutati
caso per caso rispetto al design (CLI snella, read-only, niente cache locale).

## Spunti dalla valutazione v2.0.0 (2026-08-09)

Dalla verifica live con scenari per tecnici GIS, analisti e uffici comunali
(dettagli in `docs/evaluation-v2.0.0.md`):

### Ricerca per ente (`--org` / `--suggest-org`)

Punto debole verificato: `apiso_OrganizationName_txt:"Comune di Bologna"` → 0
(testo analizzato), `EnteResponsabile_s`/prefisso IPA → 0 (comune non
indicizzato con quei nomi), wildcard su `contact_organizations_s` → over-match.
Proposta: flag `--org <nome>` che cerca in OR sui campi ente (con
`--org-exact` per la stringa esatta), oppure `--suggest-org` che stampa i
valori distinti che matchano il testo per scoprire la stringa giusta. Non tocca
i dati a monte, solo il lato query.

### Zero risultati e query invalide parlanti

Su `total=0` suggerire percorsi alternativi (es. ricerca per territorio con
`--bbox`); su `--sort` che genera HTTP 500 stampare i campi ordinabili (già
disponibili offline in `discover --what sort_values`).

### `resources` batch e con latenza

Oggi accetta un solo ID e riporta solo lo status (HEAD). Per valutare i
servizi di una ricerca intera servono argomenti multipli; per distinguere un
servizio vivo da uno lento serve il tempo di risposta della probe, non il solo
200.

### Tabella `--wide`

Le colonne title/bbox/org vengono troncate in terminali stretti. Opzione per
non troncare o per scegliere le colonne.

## Spunti da Copernicus-Services-Products-Metadata

Riferimento: <https://github.com/do-me/Copernicus-Services-Products-Metadata>

Quel progetto fa l'opposto di openrndt — snapshot statico settimanale del
catalogo committato nel repo (Parquet/CSV/Excel/JSON) + discovery locale
**retrieve-then-rerank** con cross-encoder. openrndt invece è live e read-only.
Le idee trasferibili:

### Rerank semantico sui risultati (priorità alta)

La ricerca lessicale RNDT (Solr/Lucene) premia chi ripete le parole esatte
della query. Un reranker leggero — es. `cross-encoder/ettin-reranker-17m-v1`
(~68 MB, gira su CPU) — potrebbe riordinare i top-N di `openrndt search` per
*intento* anziché per match testuale.

- Flag opzionale `--rerank` su `search`: prende i top-K, costruisce
  "product documents" compatti (titolo + abstract + keyword) e li riordina.
- Resta opzionale → non rompe il design read-only.
- Dipendenza pesante: valutare extra `pip install openrndt[rerank]` oppure
  tenerla fuori dalla CLI e solo dentro la skill.
- Da verificare: qualità del reranker in italiano (serve un PoC su query reale).

### Snapshot periodico + cronologia (GitHub Actions)

Workflow CI separato (NON nella CLI) che fa un dump periodico del catalogo RNDT.
Abilita: ricerca offline veloce, rerank senza N chiamate di rete, e soprattutto
il **diff temporale** ("cosa è stato aggiunto/modificato nel catalogo questo
mese"). Da tenere come artefatto di repo, fuori dal design no-cache della CLI.

### Output Parquet per analisi

Aggiungere `--format parquet` (preserva i tipi, ottimo per duckdb/pandas).
Coerente con l'uso analitico, basso costo. Unico formato extra che aggiunge
valore reale rispetto a json/table/csv già presenti.

### Output compatto per agenti AI — ✅ implementato

Realizzato come `--format compact` (NDJSON, una riga per record). Vedi PR #7.
Nota di design: in Copernicus il "product document" sintetico è costruito
*prima* di cercare (catalogo locale); in openrndt il catalogo è remoto, quindi
il formato compatto è solo un rendering dei risultati *dopo* la `search`.

## Da NON fare

- Snapshot dentro la CLI: violerebbe il design read-only/no-cache. Va come
  workflow separato.
- Replicare i 6 formati di output di Copernicus: ridondante. Solo Parquet
  aggiunge valore reale.
