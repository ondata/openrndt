# Valutazione openrndt 2.0.0 — utilità per tecnici GIS, analisti spaziali e uffici comunali

Data: 2026-08-09 · Versione progetto: 2.0.0 · Metodo: verifica live contro `https://geodati.gov.it/RNDT` (API reale, nessun mock), scenari realistici per ciascuna figura professionale, esecuzione della suite test (99 passanti).

## Giudizio sintetico

Strumento maturo e production-grade per la discovery sul Repertorio Nazionale dei Dati Territoriali. Per il tecnico GIS e l'analista spaziale copre l'intero flusso ricerca → dettaglio → servizio → GIS, con poco attrito. Per l'ufficio comunale è buono ma con un'attrito reale: il caso d'uso tipico ("cosa pubblica il mio comune / chi pubblica i dati sul mio territorio") è il più debole, perché la ricerca per ente è fragile e il catalogo a monte non normalizza i nomi delle amministrazioni.

## Prova sul campo — scenari provati live

| Figura | Scenario | Comando provato | Esito |
|---|---|---|---|
| Tecnico GIS | DTM nella bbox di Bologna | `search --q "modello digitale del terreno" --data-category elevation --bbox 11.2,44.4,11.6,44.8` | ✅ 78 totali, ~0.5s, enti corretti (RER, Lombardia, ISPRA, MASE) |
| Tecnico GIS | Endpoint WMS/WFS di un record | `resources ispra_rm:01IdroHazard_DT` | ✅ WMS/WFS/download con `ok=true`, `status_code=200`, probe HEAD |
| Tecnico GIS | Import in QGIS | `footprints --bbox …` → GeoJSON | ✅ FeatureCollection EPSG:4326 con id/title/org/type/resources |
| Tecnico GIS | Dati per QGIS/script | `--format csv search --q ortofoto --profile qgis` | ✅ colonne `wms_url`, `wfs_url`, `download_url`, `xmin..ymax` |
| Tecnico GIS | Metadato per INSPIRE | `get <id> --xml` | ✅ XML ISO 19139 valido (`xmllint` ok) |
| Analista | Freschezza dati | `--updated-from 2025-01-01 --sort apiso_Modified_dt:desc` | ✅ ordinamento reale per data scheda |
| Analista | Copertura temporale del dato | `--time 2015-01-01/2024-12-31 --data-category inlandWaters` | ✅ 42 totali = valore atteso documentato |
| Analista | Scrematura di massa | `--format compact search --q catasto --num 5000` | ✅ 5000 record NDJSON in 36s |
| Comune | Dati "locali" sul territorio | `--q 'AmbitoTerritoriale_s:Locale' --bbox 11.2,44.4,11.5,44.6` | ✅ 15 record per l'area di Bologna (vs 2789 con solo bbox) |
| Comune | Cosa pubblica il Comune di Bologna | `--q 'apiso_OrganizationName_txt:"Comune di Bologna"'` | ❌ 0 risultati silenziosi |
| Comune | Idem via forma breve / codice IPA | `EnteResponsabile_s:"Comune di Bologna"`, `apiso_Identifier_s:c_a944*` | ❌ entrambi 0: il comune non è nel catalogo con questi nomi |

## Punti di forza

- **Ricerca combinata tema + spazio + categoria funziona ed è veloce** (~0.5s per ricerca, opzioni `--bbox`, `--data-category`, `--q` in AND corretto). Il filtro `--time` (copertura temporale del dato) si combina correttamente con gli altri filtri e i conteggi tornano con quelli documentati (42 = atteso).
- **Output pensati per il flusso GIS, non solo per la lettura**: `--profile qgis` produce CSV già caricabile in QGIS (URL servizi + bbox separate), `footprints` esporta GeoJSON QGIS-ready, `get --xml` dà l'ISO 19139 per INSPIRE, `resources` fa health-check degli endpoint con probe HEAD (status, redirect, blocca IP privati) senza scaricare body.
- **`compact` (NDJSON)** è un'ottima scrematura a basso costo per agenti e pipeline: id/title/org/type/category/updated/resources su una riga (dalla 3.0.0 anche `indexed`, con `updated` che è ora la data della scheda). 5000 record estratti in 36s.
- **Distinzione corretta tra date della scheda e date del dato**, documentata e verificabile: `--updated-from/to` su `apiso_Modified_dt`, `--published-from/to` su `apiso_PublicationDate_dt`, `--time` sulla copertura dei dati. Per l'analista è la differenza che conta.
- **`discover` offline**: codelist ISO 19115 (19 categorie con cheat sheet bisogno→categoria), campi Lucene (31), valori di sort (incluse le trappole note) senza nessuna chiamata di rete.
- **Bug dell'API compensati e documentati su 3 livelli** (skill, reference, codice): `dataCategory` che non filtra (tradotto in `keywords_s`), sort "amichevole" ignorato, `link alternate` verso IP privato → workaround con `get`. È il valore aggiunto più grande rispetto all'uso diretto dell'API.
- **Robustezza e igiene**: 99 test passanti, mai uno stack trace (errori su stderr con exit code 0/1/2), retry su timeout/5xx, changelog e doc allineati alle verifiche live.

## Punti di debolezza

1. **Ricerca per ente senza un flag dedicato** (impatto: ufficio comunale). ~~Il campo che sembra ovvio (`apiso_OrganizationName_txt`) restituisce 0 perché è testo analizzato e la frase esatta non matcha~~ — **diagnosi errata, corretta il 2026-08-09**: quel campo funziona benissimo con la frase esatta (`apiso_OrganizationName_txt:"comune di torino"` → 269 record, un solo ente, ed è pure case-insensitive). Il Comune di Bologna dà 0 per una ragione diversa e a monte: non pubblica in proprio sul RNDT. Il difetto lato CLI era un altro — nessun flag `--org`, quindi l'utente doveva scrivere la clausola a mano e indovinare quale dei tre campi ente usare, sbagliando in silenzio (`EnteResponsabile_s` è case-sensitive; la wildcard su `contact_organizations_s` è case-sensitive *e* over-matching). **Risolto in 3.0.0**: `--org` (frase sul campo analizzato), `--org-exact` (keyword) e, su zero risultati, una query esplorativa che mostra i nomi di ente realmente in catalogo. Resta a monte la mancanza di normalizzazione dei nomi e di un identificativo IPA dell'ente.
2. **Zero risultati indistinguibili da errore di query** (impatto: tutti). Un totale `{value:0, relation:"eq"}` è legittimo o è sintassi sbagliata? E `--sort title` (senza direzione) produce un HTTP 500 con messaggio minimo, senza dire che i campi ordinabili sono due soli. La skill documenta tutto, ma chi usa la CLI senza skill si ferma.
3. ~~**Tabella terminale con colonne troncate**~~ — **smentita il 2026-08-09**: verificato con `COLUMNS=80`, Rich usa `overflow="fold"` e manda a capo senza tagliare nulla. Il difetto reale della tabella era un altro: nel profilo `default` la colonna `author` mostra la sorgente di harvest (`csw.piemonte`), non l'ente. **Risolto in 3.0.0** con l'aggiunta della colonna `org`.
4. **`updated` ingannevole** (impatto: analista distratto). Riportava l'istante di indicizzazione nel catalogo (`sys_modified_dt`, ~~uguale per tutti i record~~ — varia per record, raggruppato per batch di reindicizzazione), non la data del dato o della scheda. Il punto non era la documentazione ma una collisione di nome interna alla CLI: `--updated-from/--updated-to` filtrano su `apiso_Modified_dt`, mentre la colonna `updated` mostrava un altro campo. **Risolto in 3.0.0**: `updated` = `apiso_Modified_dt`, `indexed` = `sys_modified_dt`. Nel JSON grezzo resta la convenzione dell'API, segnalata su stderr.
5. ~~**Health-check endpoint su un record alla volta**~~ (**risolto**: `resources` accetta più ID in batch) (impatto: chi valuta i servizi di una ricerca intera). `resources` è ottimo ma monadico: per controllare gli endpoint dei 50 risultati di una ricerca serve un loop esterno (`for id in …; openrndt resources $id`), con una chiamata HTTP del catalogo per record.
6. **Sweep totale del catalogo lento** (impatto: analisti che vogliono il quadro completo). 36s per 5000 record; il catalogo è a 23.632 e cresce. Per un dump completo servono ~3 minuti e paginazione interna; accettabile, ma l'idea già in `future-ideas.md` (snapshot periodico via workflow separato) resta la risposta giusta.
7. **Flake API osservato** (non riproducibile, una sola occorrenza): una `search --num 2` con sort non supportato ha restituito 3 record. Il retry della CLI non copre questo caso (non è un errore HTTP). Da tenere d'occhio, non è un difetto dimostrato della CLI.

## Vincoli a monte (non modificabili) che pesano sull'esperienza

Questi limiti sono del catalogo e delle API RNDT: la CLI e la skill li aggirano o li documentano, non li risolvono.

- **Nomi degli enti non normalizzati**: lo stesso ente compare in molte varianti (`apiso_OrganizationName_txt`), i comuni minori spesso non pubblicano affatto o sotto il nome di un ente sovraordinato. È la causa della debolezza #1.
- **Campi data della risorsa compilati parzialmente** (36–56% dei record: creation/publication/revision). Filtrare su uno di essi scarta in silenzio chi non lo ha; solo `apiso_Modified_dt` (data della scheda) è al 100% e ordinabile.
- **`dataCategory` documentato ma non funzionante** come parametro (compensato: la CLI traduce in `keywords_s`).
- **Sort reale limitato a due campi** (`title`, `apiso_Modified_dt`); gli altri ordinamenti documentati sono ignorati o errore.
- **Link `rel=alternate` verso IP privato** (`192.168.x.x`): workaround documentato, ma ogni consumer dell'API "nuda" ci inciampa.
- **`links_s` spesso contiene pagine web, non servizi OGC**: molti record puntano a un portale (es. ambiente.regione.emilia-romagna.it) invece che a WMS/WFS. `resources` con `ok=true` può verificare che un link è vivo ma non che è un servizio interrogabile.
- **Servizi WFS degli enti lenti o instabili**: `ogrinfo` sul WFS ISPRA ha superato i 120s di timeout. La CLI verifica gli endpoint solo con HEAD; la latenza reale del servizio è fuori dal suo controllo.
- **CSW quasi inutile per la ricerca** (SortBy ignorato, nessun filtro data, queryables `apiso:*` rotti, bbox parziale 30 vs 748 record). Utile solo come layer vettoriale in QGIS/GDAL. Ben documentato, ma è un limite netto del servizio.

## Proposte nuove e migliorative

Priorità bassa/alta distinte per costo. Quello che tocca l'API o i dati a monte è segnalato come vincolato.

1. ~~**Flag `--org` / `--organization` su `search`**~~ (**fatto in 3.0.0**, con la strategia rivista: frase sul campo analizzato invece dell'OR con wildcard, che si è rivelato over-matching) (CLI, costo medio, priorità alta). Cerca sugli enti con strategia robusta: OR su `contact_organizations_s`, `EnteResponsabile_s`, `apiso_OrganizationName_txt` (con wildcard), più variante `--org-exact` per la stringa esatta. Risolve la debolezza #1 senza toccare i dati a monte. Alternativa minima: `--suggest-org <nome>` che stampa i primi valori distinti di ente che matchano il testo, così l'utente vede la stringa giusta da usare.
2. ~~**Messaggi per zero risultati e query invalide**~~ (**fatto**) (CLI, costo basso, priorità alta). Su `total=0`: suggerire varianti (es. "nessun risultato per 'Comune di Bologna': prova la ricerca per territorio con `--bbox`, o cerca l'ente con `contact_organizations_s:*bologna*`"). Su `--sort` con errore 500: stampare i campi ordinabili (già disponibili offline in `discover --what sort_values`).
3. ~~**`resources` in batch e con latenza**~~ (**fatto**; la prima versione di `latency_ms` misurava secondi e stampava sempre `0`, corretta in 3.0.0) (CLI, costo basso-medio, priorità media). Accettare più ID in una chiamata (`resources id1 id2 …`) per health-check di una ricerca intera, e aggiungere il tempo di risposta della probe oltre allo status: i 200 dicotomici non distinguono un servizio vivo da uno lento.
4. ~~**Tabella senza troncamento**~~ (**non serve**: Rich non tronca, manda a capo) (CLI, costo basso). Opzione `--wide` / colonne selezionabili per evitare il clip di title/bbox in terminali stretti.
5. ~~**Ricette "comune" nella skill**~~ (**fatto in 3.0.0**: workflow 3 della skill riscritto con `--org`, ripiego per territorio e suggerimento sui nomi reali) (skill, costo basso, priorità media). Un workflow dedicato: "dati sul mio territorio" = `AmbitoTerritoriale_s:Locale` + `--bbox` del comune + `--profile qgis`, verificato live (15 record per Bologna contro 2789 con solo bbox); e un cheat sheet per la ricerca ente con le stringhe già note.
6. **Sweep e snapshot del catalogo** (fuori dalla CLI, già in `future-ideas.md`): workflow CI separato che produce dump periodici → diff temporale e ricerca offline. Resta la risposta giusta per l'analista che vuole il quadro completo senza 3 minuti di chiamate live.
7. **Rerank semantico e output Parquet** (già in `future-ideas.md`): non ri-testati qui, rimangono validi come evoluzioni opzionali.

## Nota metodologica

Tutte le verifiche sono state eseguite oggi (2026-08-09) contro l'API reale di `geodati.gov.it`. I totali di riferimento cambiano perché il catalogo cresce: "catasto" oggi dà 8.832 (8.827 al 2026-07-17). Un'occorrenza di `--num 2` che ha restituito 3 record non è stata riproducibile ed è riportata come flake, non come bug.