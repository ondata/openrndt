# Idee future

Spunti raccolti per evoluzioni di openrndt. Non sono impegni: vanno valutati
caso per caso rispetto al design (CLI snella, read-only, niente cache locale).

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

### Output compatto per agenti AI

Un formato `--format compact` (o `--agents`): una riga sintetica per record
(id, titolo, ente, categoria, risorse) per far scremare velocemente l'agente
senza ingoiare JSON completi.

Nota: in Copernicus il "product document" sintetico è costruito *prima* di
cercare, perché il catalogo è locale e la ricerca è locale. In openrndt il
catalogo è remoto: la ricerca la fa RNDT, quindi non c'è un "prima" — il
formato compatto è solo un **rendering dei risultati dopo** la `search`, cioè
un'opzione di output di `search`. Niente pre-indicizzazione.

## Da NON fare

- Snapshot dentro la CLI: violerebbe il design read-only/no-cache. Va come
  workflow separato.
- Replicare i 6 formati di output di Copernicus: ridondante. Solo Parquet
  aggiunge valore reale.
