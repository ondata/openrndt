# Valutazione openrndt 3.0.0 — idoneità come backend per una CLI agentica

Data: 2026-08-09 (rifatta dopo un primo tentativo viziato — vedi nota metodologica) · Versione CLI installata: 3.0.0 (PyPI) · Skill valutata: `skills/rndt-explorer/SKILL.md` del repository (`md5: 1cc9b59b7d7d5144c4272627d3eccf30`), letta per percorso esplicito, non per nome — vedi perché nella nota metodologica · Metodo: esecuzione live di scenari end-to-end per due figure, tecnico GIS e ufficio tecnico di una PA, seguendo esattamente quello che la skill dichiara e verificando ogni sua affermazione contro il comportamento reale.

## Giudizio sintetico

Sì. Con la skill corretta effettivamente in mano, quello che dichiara e quello che la CLI fa dal vivo coincidono in ogni punto verificato — atteso, visto che skill e CLI sono state scritte e rilasciate insieme, ma non scontato, ed è la prima cosa da controllare prima di fidarsi di una skill. Un flusso PA realistico (trova l'ente → dettaglio → verifica endpoint) gira in circa un secondo; un flusso GIS (tema+bbox+categoria → risorse → footprint QGIS) altrettanto. Errori azionabili senza umano in mezzo, formati calibrati sul contesto di un agente, guardrail di sicurezza già pensati per input non curato. Il limite reale non è nella coppia CLI+skill così com'è scritta, ma in un fatto verificato in questa stessa sessione poco prima di questa valutazione: **il meccanismo con cui un agente carica "la skill" per nome non garantisce che sia questa** — esiste una seconda copia, omonima, installata altrove e non più sincronizzata, e il tool di risoluzione ha caricato quella sbagliata anche sotto istruzione esplicita. Il rischio quindi non è nel contenuto della skill, ma nella fiducia che un agente può darle senza verificarne prima la provenienza.

## Scenari verificati live

### Tecnico GIS, fase per fase come da skill

| Fase | Comando | Esito | Tempo |
|---|---|---|---|
| 1 — discovery offline | `discover` | 5 sezioni (categorie, campi Lucene, formati, parametri, sort), 6,5KB, nessuna chiamata di rete | 0,15s |
| 2 — ricerca con filtri progressivi | `search --q "modello digitale del terreno" --data-category elevation --bbox 11.2,44.4,11.6,44.8 -n 3` | 3 risultati pertinenti (Regione Lombardia, Regione Emilia-Romagna, ISPRA) | 0,48s |
| 3 — dettaglio XML per INSPIRE | `get <id> --xml` | XML ISO 19139 valido (`xmllint` conferma), 103KB | 0,42s |
| 4 — risorse in batch su 3 record | `resources <id1> <id2> <id3>` | `count: 3`, per-record `resources[]` con `ok`/`latency_ms` | 1,4s |
| export QGIS | `footprints --q … --data-category elevation --bbox … -n 3` | GeoJSON valido, `features_with_bbox: 3`, proprietà con `updated`/`indexed` distinti | 0,36s |

### Ufficio tecnico PA, incluso l'esempio letterale della skill

| Passo | Comando | Esito | Tempo |
|---|---|---|---|
| Cosa pubblica il Comune di Torino | `--org "comune di torino"` | 3 record, `org` corretto in ogni riga | 0,38s |
| Zero risultati su un ente che non pubblica in proprio (l'esempio esatto della skill) | `--org "comune di bologna"` | 0 risultati **con la stessa identica risposta che la skill promette**: `Citta' metropolitana di Bologna \| Agenzia Regionale per La Sicurezza Territoriale \| Regione Emilia-Romagna` | 0,85s |
| Dettaglio, contatto, licenza | `get <id>` | `EnteResponsabile_s: Comune di Torino`, `PuntoDiContattoEmail_s: geoportale@comune.torino.it`; licenza `n/d` su questo record — campo `isOpendata` non compilato, coerente con `known-issues.md` | 0,36s |
| `--org` anche su `footprints` (documentato in skill) | `footprints --org "comune di torino" -n 2` | GeoJSON filtrato correttamente sull'ente | 0,33s |
| **Flusso end-to-end** (org → get → resources) | 3 comandi in sequenza | — | **~1s totali** |

### Altre affermazioni della skill, verificate una per una

- **Promemoria su `--sort` in errore**: `search --sort title -n 1` (senza direzione) → HTTP 500, messaggio su stderr identico a quello che la skill riporta, exit `1`. Confermato.
- **Costo in contesto di `json` vs `compact`**: 5 record via `--format json` pesano 178.157 byte, via `compact` 1.358 — rapporto 131×. La skill raccomanda `compact` per lo screening e `json` solo sul record scelto: confermato che è l'unica scelta sensata per un agente con budget di contesto.
- **Leading wildcard su campo `_s` esplicito**: la tabella della skill lo dà per bloccato. Il controllo diretto è risultato inconcludente — `apiso_Type_s` ha solo tre valori distinti (`dataset`/`series`/`service`), quindi `*ataset` e `dataset*` restituiscono lo stesso totale di `dataset` esatto sia che il wildcard funzioni sia che venga ignorato. Non lo marco né confermato né smentito: serve un campo `_s` con più valori distinti per un test dirimente.

## Cosa rende la coppia CLI+agente affidabile

- **Errori azionabili senza umano in mezzo**: ogni fallimento testato (sort non valido, timeout di rete, ente non trovato) esce con un `exit code` distinto e un messaggio che dice cosa fare dopo, non solo cosa è andato storto.
- **Guardrail di sicurezza pensati per input non curato**: `resources --check` blocca IP privati, loopback, link-local e DNS che risolve verso indirizzi riservati, prima di contattarli. Rilevante perché gli URL vengono da un catalogo pubblico, non filtrato editorialmente.
- **La skill non mente quando è quella giusta**: ogni comando, ogni esempio, ogni promessa di comportamento su zero risultati verificati oggi corrisponde esattamente a quanto scritto. Non è un dettaglio da dare per scontato — è quello che il tentativo precedente di questa stessa valutazione ha dimostrato poter mancare.

## Punti deboli

1. **Un agente non ha, oggi, un modo affidabile di sapere se la skill che ha appena caricato è questa o una copia vecchia con lo stesso nome.** Non è un'ipotesi: è quello che è successo nel tentativo precedente di questa valutazione, con istruzione esplicita a usare la cartella del progetto. `SKILL.md` porta già un campo `metadata.version` (`"2.0"`, mai aggiornato) che potrebbe essere confrontato con `openrndt --version` a ogni caricamento, ma oggi nessun meccanismo lo fa.
2. **`--bbox` malformato non è validato lato client e ritorna silenziosamente l'intero catalogo.** `--bbox "non,valido"` esce `0` con `total: 23673`, lo stesso numero di nessun filtro affatto — è l'API RNDT a ignorare il parametro, non un bug della CLI, ma è un punto validabile prima della richiesta sullo stesso principio già usato per date e `bbox_crs`. Per un agente che controlla solo l'exit code o `total > 0`, un bbox scritto male da un passaggio precedente (es. una geocodifica) sembra un successo.
3. **"Cosa pubblica il mio comune" resta senza risposta per una minoranza di comuni**, indipendentemente da quanto sia buono `--org`: se l'ente non pubblica in proprio sul RNDT, nessuna sintassi lo trova. Non è un difetto della CLI (già segnalato ad AgID), ma la skill giusta lo gestisce bene — lo suggerisce lei stessa come fallback territoriale — mentre la skill vecchia lascerebbe un agente bloccato proprio lì.

## Cosa serve prima di considerarlo pronto per un servizio esposto

1. **Versionare `SKILL.md` in modo verificabile a runtime** e far controllare a un agente, prima di fidarsi del contenuto, che `metadata.version` combaci con `openrndt --version` (o quantomeno che i comandi citati esistano ancora, via `--help`). Costo basso, priorità alta — è l'unico punto di questa valutazione con un impatto dimostrato, non solo plausibile.
2. **Validazione client-side del formato bbox**, stesso pattern già usato per le date. Costo basso, priorità media.
3. La skill già gestisce bene il fallback territoriale sul caso ente-non-pubblica-in-proprio; vale la pena solo assicurarsi che resti la prima cosa letta, non un dettaglio in fondo alla sezione zero-risultati.

## Nota metodologica

Questa è una ripetizione della valutazione fatta poco prima nella stessa sessione. La prima volta la skill era stata caricata con l'invocazione per nome (`Skill(rndt-explorer)`), e nonostante l'istruzione esplicita a usare quella della cartella del progetto, il tool ha risolto sulla copia omonima installata nella home dell'utente (`~/.agents/skills/rndt-explorer`), ferma a prima del rilascio 3.0.0 e quindi priva di `--org`. Quella valutazione era corretta sui dati live (la CLI usata era comunque la 3.0.0 reale) ma scorretta nel giudicare "la skill", perché la skill giudicata non era quella del progetto. Questa volta il file è stato letto per percorso esplicito e verificato con un hash prima di procedere, eliminando l'ambiguità. La discrepanza fra le due copie, e il fatto che il meccanismo di risoluzione per nome l'abbia imboccata anche sotto istruzione esplicita, restano un finding valido di questa valutazione — riportato al punto 1 dei punti deboli — perché è successo davvero, nella stessa sessione, in condizioni d'uso normali.
