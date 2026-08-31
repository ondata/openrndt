# LOG

## 2026-08-31 (correzioni post-valutazione; skill 3.4.0)

- **Chiusi i rilievi della valutazione**. Parità CLI/libreria: `item_record`, `contact_point`, `download_urls`, `bbox_from_envelope` esportati da `openrndt`. `--raw` con `--xml`/`--html` ora è un `BadParameter` invece di un'opzione ignorata in silenzio. README aggiornato in tre punti (documento normalizzato con la dichiarazione di additività, `email`/`download` in `compact`, `item_record` nella sezione libreria), che era l'unica documentazione rimasta alla 3.2.0.
- **Set di ruff dichiarato**: `select = ["E", "W", "F", "I"]`, `ignore = ["E402", "E501"]`. Il default (`E4`, `E7`, `E9`, `F`) non vedeva né lo spazio in coda in `search.py` né gli import fuori ordine, quindi «ruff pulito» diceva meno di quanto sembrasse. Fermato lì e non su `B`/`UP`: quelle regole colpiscono solo codice preesistente e non toccato (`B008` è l'idioma obbligato di Typer, `B904` sono i `raise typer.Exit` dei gestori).
- **Skill alla 3.4.0**: `compatibility` da `>= 3.1.0` a `>= 3.3.0` (insegnava `--raw`, che su una 3.1.0 non esiste), e le sette ricette che ricostruivano a mano da `_source` quello che ora è al primo livello. Le due riscritte sono state riprovate contro l'API viva su `ispra_rm:01IdroHazard_DT`.
- Suite a 158 test (due nuovi), ruff e mypy `strict` puliti.

## 2026-08-31 (valutazione della CLI 3.3.0 e allineamento della skill)

- **Valutazione in `docs/evaluation-cli-v3.3.0.md`** (nome distinto perché `docs/evaluation-v3.3.0.md` è la eval di triggering della skill, numerazione diversa). Verifiche contro l'API viva: il contratto documentato di `get` coincide chiave per chiave con l'output reale; il permalink costruito da `item_record` è identico a quello estratto da `record_url`; su 300 record nessuno perde risorse per l'asimmetria `resources_nst` (`get`) contro `links` (`compact`), e i campi array (`apiso_Lineage_txt`, 263/300) hanno sempre un solo elemento, quindi `_first_str` non scarta nulla di misurabile.
- **Verificata l'additività invece di dedurla**: `get --raw` contro `get` sullo stesso record, le sette chiavi della busta escono identiche e le sedici nuove si aggiungono senza collidere. La 3.3.0 è quindi numerata bene (minor, sotto *Added*); il difetto è solo nella voce di changelog, che dice «invece della busta» e non dice che nessuna chiave preesistente cambia.
- **Rilievo principale**: nessuno dei quattro helper nuovi (`item_record`, `contact_point`, `download_urls`, `bbox_from_envelope`) è esportato in `__init__.py`, contro la convenzione tenuta in 3.0.0 e 3.1.0, e il README non cita né `--raw` né il documento normalizzato: la documentazione per agenti è aggiornata, quella per umani no.
- **Altri rilievi**: il permalink è hardcoded e ignora `OPENRNDT_BASE_URL`; `--raw` con `--xml` viene ignorato in silenzio mentre `--xml --html` dà errore; `ruff check` passa perché la configurazione resta al set di default (`E4,E7,E9,F`) e non vede il `W291` in `search.py:449`.
- **Skill `rndt-explorer`**: allineata dove il commit l'ha toccata (`compact` con `email`/`download`, `result-structure.md` con il documento normalizzato e `--raw`), ferma alla 3.2.0 nelle altre reference: `compatibility` dichiara ancora `>= 3.1.0` mentre insegna `--raw`, `SKILL.md:204` chiama il default «JSON Elasticsearch», la Fase 4 e `output-formats.md` mandano ancora a `_source.links_s`, la lista dei campi di `compact` in `output-formats.md` non ha `email`/`download`, e `workflows.md:207` ricostruisce a mano i tre campi che ora sono al primo livello.

## 2026-08-31 (v3.3.0 - output CLI: get normalizzato, compact email+download)

- **`get` normalizzato** (verificato su API reale): parte dal confronto col mirror CKAN di dati.gov.it, dove email/licenza/bbox sono solo proiezioni del RNDT grezzo. `_source` li ha già ma l'output JSON sputava la busta ES. Ora `--format json` (default) costruisce il documento: id/title/org/type/category, date updated (scheda) e indexed, `data_date` (del dato), `contact` (name/email/website da `PuntoDiContatto*`), `bbox` (da `envelope_geo`), `lineage`, `resources` (come `resources --no-check`) e `url` permalink; `_source` preservato. `get --raw` ripristina la busta. 3.3.0 chiude il gap: `result-structure.md` documentava già il normalizzato che la CLI non emetteva.
- **`resources` ora legge `resources_nst`**: risorse tipizzate dal catalogo (`url_s`+`url_type_s`) con precedenza su links/links_s/webServices_s, dedup per URL (verificato: source WMS/WFS diventa `resources_nst`).
- **compact + `email` e `download`**: scremata a basso costo con "chi contatto / come scarico". Fields da `PuntoDiContattoEmail_s` (500/500 su campione) e `url_download_s`+`url_http_download_s` (488/500), tipi misti normalizzati.
- Nota: il `jq` sul PATH della shell di sessione è un builtin che si autodichiara jaq 2.3.0; jq vero = `/home/aborruso/bin/jq` (jqlang 1.7.1).

## 2026-08-31 (eval di triggering della descrizione)

- Costruita con l'utente una eval di trigger: 21 query approvate una a una (10 positive, 11 negative costruite sui quasi-raggiungimenti delle skill concorrenti) più 6 di holdout, 3 run per query, giudice = modello di sessione con la lista reale delle concorrenti. Baseline: recall 10/10 ma 2 falsi positivi (geoportale regionale da sfogliare, Corine Land Cover europeo). Applicata la V2 (scope catalogo nazionale dei metadati + non-goal espliciti): 21/21 sul set, 6/6 su holdout, riprova post-applicazione 4/4. Dataset in `skills/rndt-explorer/evals/trigger-evals.json`, misure in `skills/rndt-explorer/evals/trigger-results.json`, dettagli in `docs/evaluation-v3.3.0.md`.

## 2026-08-30 (skill sfoltita: SKILL.md da 464 a 371 righe)

- Spostati nelle reference i blocchi che erano cresciuti nel corpo: conteggio difendibile e nota completa su `isOpendata` in `workflows.md` §11, ricetta «ente che non pubblica in proprio» in §12, operatori e tabella wildcard in `search-syntax.md`, campi del check di `resources` in `result-structure.md`. In `SKILL.md` restano la regola operativa e il rimando. Il filo delle cinque fasi torna leggibile senza perdere nulla: le reference passano da 1465 a 1623 righe.


## 2026-08-30 (iteration-2 della valutazione skill, e quattro correzioni)

- **Iteration-2**: 5 casi, skill attuale contro lo snapshot di stamattina (`0441063`), grading indipendente per caso. Pass rate identico (96,6%), ma i punti si spostano: la nuova vince su Padova (6/6 contro 5/6: aggrega per ente, distingue `apiso_OrganizationName_txt` da `EnteResponsabile_s`, cita 40 id verificabili, mentre la vecchia ne cita uno solo), perde sul conteggio idrografia (5/6 contro 6/6: costruisce un universo più largo senza misurarne il rumore, e il 231 pubblicato contiene ortofoto e immagini satellitari). Su scheda catastale, WMS e footprints pareggio, con la nuova migliore nel merito (data confermata dall'XML, scelta consapevole fra duplicati, copertura 82 contro 71 record).
- **Errore non intercettato da nessuna assertion**: nell'eval 3 la versione nuova ha scartato il layer 1:100.000 citando un limite di scala che è del layer 2 (236.235 contro 944.940, verificato oggi sul GetCapabilities), consegnando il 1:500.000. Da qui la correzione sui limiti di scala.
- **Quattro correzioni alla skill**: chiavi di `resources` (`type`/`url`, non `dctype`/`href` come in `links[]`); controllo del rumore dentro il perimetro prima di pubblicare un conteggio, con le tre ricette `jq`; limiti di scala da leggere sul layer che si intende usare più il conteggio dei colori della tile (verificato: layer 1 dà 54 colori su Roma e 1 su tutta l'Italia); e riformulazione delle tre consegne GeoLibre, dove `export_html` non è "una pagina chiusa per chi deve solo guardare" ma l'applicazione dentro una pagina, che permette a chi riceve di aggiungere layer, confrontare e interrogare - l'interfaccia di editing è il prezzo di questo, non un difetto.


## 2026-08-30 (skill: terza consegna, l'URL di GeoLibre Web)

- **GeoLibre Desktop e CORS, misurato** con un progetto di cinque layer: i GeoJSON da URL (`add_vector_layer`) si vedono anche senza header CORS (FVG), le tile WMS no (FVG, e ISPRA ArcGIS col doppio header); con header singolo tutto si vede. La desktop legge i vettoriali per via nativa e le tile in webview. Tabella in `geolibre.md`. Nel campione di 3000 record nessun link punta direttamente a un `.geojson`: il GeoJSON da condividere lo si produce da un WFS o da `footprints`.
- **Ridimensionata dopo la sonda sul catalogo**: su 3000 record `dataset`, 163 endpoint WFS per 2041 link; 98 vivi, 70 con GeoJSON, 48 con CORS: 236 link (11,6%), quasi tutti Sardegna e Bolzano; l'Agenzia delle Entrate (1437 link) non emette GeoJSON. La consegna 3 è ora «URL a un file che pubblichi tu» (progetto o footprints su gist/Pages); l'URL diretto a un WFS di un ente resta come nota con i numeri. Chiarito che il vincolo CORS vale per tutte e tre le consegne, HTML compreso: la pagina non contiene i dati e da `file://` l'origine è `null`.
- **`geolibre.md`, sezione «Condividere con un URL»**: `web.geolibre.app/?data=<dato>` e `?url=<progetto>`, provati su casi RNDT. Si apre: la `GetFeature` GeoJSON di Regione Sardegna (un solo `Access-Control-Allow-Origin: *`), un `footprints.geojson` su gist, un `.geolibre.json` su gist con `?url=`. Non si apre: FVG (GeoJSON ma niente CORS), Agenzia delle Entrate (niente GeoJSON). Regole: percent-encoding del valore di `data`, niente parametro di vista quindi via le bbox nazionali/mondiali prima di pubblicare, pre-check `curl -H Origin` con una sola riga CORS, raw di gist pinnato al commit.

## 2026-08-30 (skill: due consegne per GeoLibre)

- **`geolibre.md` e Fase 5**: regola delle due consegne. Il file progetto `.geolibre.json` è la fonte (JSON leggibile, modificabile, con `metadata` RNDT) e va a chi ha GeoLibre Desktop; la pagina di `export_html` è chiusa e va a chi deve solo guardare. Il progetto si conserva sempre. Motivo: [opengeos/GeoLibre#2163](https://github.com/opengeos/GeoLibre/pull/2163) (mergiata oggi) registra `.geolibre` come tipo di file di sistema, e da lì il progetto diventa apribile con un doppio clic. Finché `geolibre-mcp` vuole un path `.json`, si salva `.geolibre.json`, compatibile anche dopo. Dichiarato che il progetto non aggira CORS/`http`: la desktop è la stessa MapLibre in webview.


## 2026-08-30 (valutazione della skill rndt-explorer con test reali; CLI 3.2.0)

- **Cinque casi di test** (ente che non pubblica, lettura scheda con licenza e date, conteggio open data "difendibile", WMS su mappa condivisibile, footprints per QGIS) eseguiti da subagenti con e senza skill, più un check statico di tutti i comandi della skill contro l'API viva. Risultati in `skills/rndt-explorer-workspace/iteration-1/`. Pass rate identico (97%) perché le assertion erano poco discriminanti; la differenza è di merito: con skill la data usata è quella del dato e non della scheda, il permalink è quello canonico, la scheda scelta è la più recente. Nel caso "ente che non pubblica" la baseline è stata più completa (AVEPA, comuni della cintura): aggiunto un passo di completezza alla ricetta.
- **Tre difetti della CLI corretti (3.2.0)**: `discover` diceva «AND implicito» e «leading wildcard non supportato su campo», entrambi falsi (lo spazio è OR: `catasto siciliana` 8.903 = `catasto OR siciliana`, con AND 1); `sort_values` dava `relevance` per verificato; `resources` dichiarava morto `sgi2.isprambiente.it` (solo TLS 1.2 `AES128-SHA`, rifiutato da OpenSSL a SECLEVEL 2) - ora la probe usa `@SECLEVEL=1` e riprova in GET su errore di trasporto.
- **Skill 3.3.0**: nota storica al posto dell'avviso su `192.168.3.34` (bug RNDT risolto); esempio «solo dataset» che dava 0 sostituito; numeri di riferimento al 2026-08-30; `indexed` non è nel csv/table di default; il tipo di data (`revision`/`creation`) si conferma solo dall'XML; duplicati AdE (schede 2021 senza licenza vs 2025 CC BY); `ok=true` di `resources` non prova che un WMS serva mappe (PCN: GetCapabilities 200, GetMap `ServiceException`) con ricetta GetMap; CORS con due `Access-Control-Allow-Origin` (ArcGIS ISPRA) che blocca GeoLibre/MapLibre ma non Leaflet; workflow §10 con ricetta jq fissa per classificare le bbox (locale/regionale/nazionale/mondo), verificata: 82 record, 1 siciliano.


## 2026-08-29 (guida GeoLibre nella skill: dai risultati di ricerca alla mappa)

- **`references/geolibre.md` diventa una guida operativa** (274 righe): i tre esiti che ha senso mettere su mappa - dove stanno i dataset trovati (`footprints`), il dato via servizio (WMS), il dato vero (WFS o file) - ciascuno con la sequenza di comandi, più una sezione su altri usi sensati, la tabella sintomo/causa/verifica e il pre-check GDAL come regola trasversale.
- **Verificati due percorsi nuovi.** `footprints` → `add_geojson_layer` → `classify_layer`: la classificazione vuole una colonna numerica, mentre `resources` è un array e `open` un booleano, quindi serve un passaggio `jq` che derivi `n_risorse`; su 40 record "uso del suolo" solo 8 avevano risorse collegate. E il join `footprints` + `openrndt resources` per colorare le bbox in base a quanti endpoint rispondono: su 8 record, 7 senza alcuna risorsa e l'ottavo con una viva su due.
- **WFS: `srsName=EPSG:4326` non è opzionale.** Senza, un GeoServer regionale ha risposto in EPSG:7791 (`[555955, 4377948]` invece di `[9.65, 39.55]`): in una mappa web il dato finisce fuori dal mondo. La `GetFeature` con `outputFormat=application/json` è per il resto un URL GeoJSON che `add_vector_layer` prende così com'è.
- **Dichiarato cosa non è verificato**: WMTS, WCS, GeoTIFF/COG ed Esri MapServer/ImageServer. Su questi ultimi il campione è concentrato su pochi host e quelli provati non rispondevano (host che non risolve, timeout).

## 2026-08-29 (ponte verso GeoLibre: reference nella skill, due issue e una PR upstream)

- **Nuova reference `skills/rndt-explorer/references/geolibre.md`** e Fase 5 in SKILL.md: come portare un record RNDT su una mappa [GeoLibre](https://geolibre.app) con la skill e il server MCP di quel progetto. Sei regole ricavate provando su record veri, non dedotte: il nome del layer WMS non sta nel metadato (si ricava dal GetCapabilities o dal link GeoNode); gli endpoint catalogati in `http` vanno promossi a `https` o la webview blocca le tile; la risorsa va provata prima con `gdalinfo`/`ogrinfo`, che gira sullo stesso GDAL che usa GeoLibre e intercetta https, CORS e supporto alle `Range`; i layer WMS vanno scritti con `source.bounds` o lo «zoom to fit» non fa nulla; lo swipe fra due WMS richiede due id per lato; un file locale va inlineato, perché il lettore vive nel filesystem virtuale della pagina e non vede il disco.
- **Misurata la disponibilità di risorse sul catalogo** (3000 record): WMS 2131, WFS 1938, shapefile zippato 917, Esri MapServer 159, GeoTIFF 30, WMTS 18, WCS 15, ImageServer 13, GeoPackage 12.
- **Skill alla 3.2.0 e `skills-lock.json` non più tracciato**: `metadata.version` è la versione della skill e non della CLI, la versione minima di CLI si dichiara in `compatibility` (`>= 3.1.0`); la convenzione è in `knowledge/skill.md`. Il lockfile lo scrive `npx skills` e registra l'installazione locale della skill, path assoluto della macchina compreso: non descrive il progetto, è passato in `.gitignore`. Il suo `computedHash` era fermo al commit iniziale della v0.1.0.
- **Tre segnalazioni a GeoLibre**: [issue #2153](https://github.com/opengeos/GeoLibre/issues/2153) (shapefile zippato da URL: funziona nell'app desktop, fallisce sul web con un errore GDAL che non dice la causa), [issue #2154](https://github.com/opengeos/GeoLibre/issues/2154) (drag & drop di un file progetto per cambiare progetto invece di aggiungere un layer), [PR #2155](https://github.com/opengeos/GeoLibre/pull/2155) (`add_swipe` scriveva solo l'id del layer di progetto: per i tipi raster il controllo agisce su `layer-<id>-raster`, quindi il layer restava senza lato e veniva disegnato su entrambe le metà; tre test aggiunti, suite di 325 test verde).

## 2026-08-29 (release 3.1.0)

- **Rilasciata la 3.1.0**: bbox validata lato client, campi `open`/`license`/`url` negli output sintetici, codelist `AmbitoTerritoriale_s` corretta, skill `rndt-explorer` riverificata comando per comando. PR #16, mergiata in rebase.

## 2026-08-29 (bbox validata, licenza e permalink negli output, skill riverificata)

- **`--bbox` è validata prima della chiamata**: quattro valori numerici, longitudini in -180..180, latitudini in -90..90, `xmin < xmax`, `ymin < ymax`; `ValueError` che la CLI traduce in exit 2. Chiude un falso successo verificato: `--bbox "non,valido"` e `--bbox "12,45,11"` restituivano 23.738 record con exit 0, cioè il catalogo intero a chi aveva chiesto una provincia, perché l'API ignora in silenzio una bbox malformata. Era la raccomandazione 2 di `docs/evaluation-v3.0.0.md` del 9 agosto, rimasta aperta.
- **Nuovi campi `open`, `license` e `url`** in `compact`, nei tre profili `csv`/`table` e nelle proprietà di `footprints`. `open`/`license` vengono da `isOpendata` e sono riportati come sono, senza normalizzare: misurato su 3000 record, il campo è presente sul 72% (55% escludendo l'Agenzia delle Entrate, 1177 record da sola) e in un terzo dei casi contiene il solo marcatore `opendata`. `url` è il permalink `rel=alternate text/html` della scheda, presente su 200 record su 200 nel campione. Nuovi export `record_license` e `record_url`; `__all__` passa da 10 a 12 voci.
- **Resa a terminale distinta**: in `--format table` `url` non si stampa, `open` esce sì/no e `license` è troncata a 60 caratteri, perché il campo del RNDT contiene spesso paragrafi interi. In `csv`, `compact` e `footprints` i valori restano interi. L'header CSV cambia: è una modifica additiva, da rilasciare come 3.1.0.
- **Skill `rndt-explorer` riverificata comando per comando** (90 comandi estratti da SKILL.md e dalle 7 reference ed eseguiti live). Tre correzioni: la tabella dei wildcard dava il leading wildcard per bloccato sui campi con nome esplicito e non lo è (`EnteResponsabile_s:*Siciliana` → 62, come la frase esatta, mentre senza asterisco → 0; quando una wildcard su `_s` dà 0 la causa è la case-sensitivity); la ricerca per ente ospite di un ente sovraordinato ha ora una sequenza misurata (nomi suggeriti dalla CLI, poi frase esatta del territorio con 13 record tutti pertinenti, poi territorio più bbox o ente sovraordinato) al posto di `--bbox` + `AmbitoTerritoriale_s:Locale`, che copre 41 record su 3000 e lascia passare i record a estensione nazionale; nota sulla copertura reale di `isOpendata`. Sanata anche la contraddizione fra SKILL.md e `search-syntax.md` su `contact_organizations_s`.
- **`codelists.py`**: `AmbitoTerritoriale_s` era documentato come `Nazionale | Regionale | Provinciale | Comunale`. `Provinciale` e `Comunale` non esistono in catalogo: i valori reali sono `Regionale` 1811, `Nazionale` 156, `Locale` 41 su 3000, più `Regional`/`Local` in inglese, e il campo manca sul 28%. Era `discover --what lucene_fields` a dire il falso.
- **Riverificate le sette segnalazioni inviate ad AgID** (18 luglio e 10 agosto): risolta solo la quarta, i link `rel=alternate` non contengono più l'IP privato `192.168.3.34` né nell'API né nel GetCapabilities CSW. Restano aperte «Considera valori vuoti», il sort per data di pubblicazione, gli esempi della guida CSW (ma `[object Object]` è diventato un intero valido), `dataCategory` che non filtra, la licenza non selezionabile e la ricerca per ente. Dettaglio in chat, non ancora in un documento.
- 146 test verdi (5 nuovi sulla bbox, 6 su licenza e permalink), ruff e mypy puliti. Aggiornati README, `knowledge/` (output-formats, error-handling, cli/search, cli/footprints, library/python-api) e la skill.

## 2026-08-29 (skill /new-command, valutazione per l'adozione)

- **Valutazione 3.0.0 dal punto di vista di tecnici GIS, giornalisti e ricercatori** in `docs/evaluation-v3.0.0-adozione.md`: benestare al lancio pubblico. Flusso completo verificato oggi, dal record `arpa_ve:Stato_Chimico_Fiumi_DGR_3_2022` al GeoPackage del layer descritto (867 punti) in circa 3,3 secondi, con in mezzo un passaggio manuale: gli URL che `resources` restituisce sono `GetCapabilities` dell'intero GeoServer, e il nome del layer va ricavato a mano dal link GeoNode del metadato; esempio 6 del README rifatto, 107 endpoint WMS in 11 secondi (il README ne dichiara 108). Difetti lato CLI in ordine di gravità: bbox non validata (`--bbox "non,valido"` e `--bbox "12,45,11"` restituiscono il catalogo intero con exit 0, raccomandazione già scritta il 9 agosto e non implementata), licenza e permalink della scheda assenti da `compact`/`csv`/`table`/`footprints`, chiavi diverse per la stessa cosa fra `search` (`href`/`dctype`) e `resources` (`url`/`type`).
- Aggiunta in locale (non versionata, `.claude/` è gitignored) la skill `/new-command`: procedura per aggiungere un comando alla CLI coprendo i sette punti che deve toccare (modulo di dominio, `cli.py`, `__all__`, test mockati, `knowledge/cli/` + `cli/index.md` + `library/python-api.md`, README, skill `rndt-explorer`). Nasce dal fatto che nessun controllo esistente vede un comando arrivato a metà: ruff, mypy e la suite passano lo stesso, e `docs-drift.sh` è a grana di directory.
- Trovate due derive di documentazione, non ancora corrette: `knowledge/conventions/output-formats.md` elenca i campi di `compact` senza `indexed` (che `cli.py` emette dalla 3.0.0, e il README documenta); `knowledge/library/python-api.md` dichiara un `__all__` di 7 voci mentre ne ha 10 (mancano `compact_results`, `record_dates`, `organization_names`).

## 2026-08-09 (v3.0.0: date separate, ricerca per ente, fix latency)

- **`updated` e `indexed` non sono più lo stesso campo**. In `table`/`csv`/`compact`/`footprints`, `updated` è ora `apiso_Modified_dt` (data della scheda, quella su cui filtrano `--updated-from/--updated-to`) e `indexed` è `sys_modified_dt` (indicizzazione nel catalogo, il campo top-level `updated` dell'API). Era una collisione di nome interna alla CLI: si filtrava su un campo e se ne leggeva un altro, e dopo `--sort apiso_Modified_dt:desc` la colonna mostrata era scorrelata dall'ordine. Verificato live: record catasto con `updated 2026-04-25T15:37:34Z` e `apiso_Modified_dt 2019-11-13`. Rottura del formato → **3.0.0**.
- Dove non si può rinominare (`--format json`, passthrough del payload API) la CLI stampa una nota su stderr, ma solo quando la ricerca usa un filtro o un ordinamento sulle date; la tabella porta la legenda in calce.
- **`--org` / `--org-exact` su `search` e `footprints`**. `--org` cerca la frase su `apiso_OrganizationName_txt` (campo analizzato: case-insensitive, ordine dei token irrilevante). Verificato live: `--org "comune di torino"` → 269 record, tutti e soli del Comune di Torino. `--org-exact` resta per il confronto esatto su `EnteResponsabile_s`.
- **Su zero risultati con `--org` la CLI mostra i nomi reali in catalogo**: una sola query esplorativa sul token più distintivo, aggregata a valle (l'API ignora `facet`, verificato). `--org "comune di bologna"` → `Citta' metropolitana di Bologna | Regione Emilia-Romagna`: il Comune di Bologna non pubblica in proprio.
- **Fix `latency_ms` sempre 0** in `resources --check`: la durata era misurata in secondi ed emessa come millisecondi. ISPRA WMS/WFS/download passano da `0/0/0` a `147/139/129` ms. Il test esistente passava anche col bug (`isinstance(int)` e `>= 0`): ora la durata è iniettata e il valore atteso è esatto.
- **Corretto un suggerimento sbagliato introdotto ieri**: su zero risultati la CLI consigliava per gli enti `contact_organizations_s:*nome*` definendolo «esatto e case-sensitive». Live: `*bologna*` → 0, `*Bologna*` → 112 ma quasi tutti di Regione E-R e ARPAE che *nominano* Bologna. Ora rimanda a `--org`.
- Tabella profilo `default`: aggiunta la colonna `org`. `author` contiene la sorgente di harvest (`csw.piemonte`), non l'ente.
- Verificata e smentita la debolezza «colonne troncate» del report: Rich usa `overflow="fold"`, manda a capo senza perdere caratteri.
- API di libreria: `record_dates()` e `organization_names()` esportate al top-level insieme a `compact_results()`.
- Test 123/123 verdi, ruff e mypy puliti. README, skill (`SKILL.md`, `search-syntax.md`, `result-structure.md`, `output-formats.md`, `workflows.md`) e bundle `knowledge/` allineati.

## 2026-08-09 (CLI: resources con redirect, latenza e batch)

- **`resources` segue i redirect (max 3) solo verso host pubblici**: validazione per hop con la stessa allowlist dell'URL iniziale. L'endpoint ARPA Veneto (`http://gaia.arpa.veneto.it/…`, 301→https) prima dava `ok=false` — un falso negativo su un servizio funzionante — ora `ok=true, redirected=true`. Un 3xx verso host non pubblico (es. link-local) non viene seguito: `error=redirect-blocked:…`. Mantenuta e rafforzata la postura fail-closed (niente follow cieco).
- **`latency_ms` per endpoint**: durata complessiva della probe; distingue un 200 veloce da uno lento. Verificato live: WMS/WFS ARPA Veneto 1ms dopo il redirect.
- **Batch**: `resources <id1> <id2> …` → `{"count": N, "results": [per-id]}`; errori per-record raccolti (metadato inesistente, HTTP, rete) senza fermare il batch. Formato a ID singolo invariato (retro-compatibile). Verificato live su 2 metadati (ARPA Veneto + ISPRA).
- Campi riga: `redirected`, `redirect_count`, `redirect_url` (prima destinazione) aggiunti all'output del check.
- Test: +6 (redirect bloccato vs seguito, too-many-redirects, latency, batch 2 id, batch con errore) e aggiornato il test «non segue redirect» → «blocca redirect verso host non pubblico». 106/106 verdi, ruff e mypy puliti.
- Skill aggiornata (Fase 4: batch, redirect, latency, campi del check) e `references/result-structure.md` con la tabella dei campi del check.

## 2026-08-09 (CLI: zero risultati e sort parlanti)

- **`search`/`footprints` con 0 risultati ora spiegano perché**: su stderr arrivano suggerimenti contestuali — wildcard su `--q` (solo per testo libero; per `campo:valore` ricorda che il valore è esatto e i campi `_s` sono case-sensitive), rimozione di `--data-category`/`--time`/`--bbox` uno alla volta, e per gli enti il nominativo esatto in `contact_organizations_s` oppure la ricerca per territorio (`--bbox` + `AmbitoTerritoriale_s:Locale`). Incentrato sul caso reale verificato: `apiso_OrganizationName_txt:"Comune di Bologna"` → 0.
- **Errore HTTP con `--sort` attivo → promemoria dei campi ordinabili** (`title`, `apiso_Modified_dt`; `dateAscending`/`dateDescending`/`relevance` ignorati; rimando a `discover --what sort_values`). Verificato live: `--sort title` (senza direzione) → 500 con contesto leggibile.
- Test: +2 (hint su stderr in json con `total` a oggetto, sort-500 con campi ordinabili), estesi i due zero-results esistenti (csv, compact) con l'assert sui suggerimenti. 101/101 verdi.
- Skill `rndt-explorer` aggiornata: sezione «Zero risultati? Leggi i suggerimenti» in Fase 2 (cause ricorrenti: periodo vuoto, ente non indicizzato, bbox nazionale), nota sort-500, e sezione dedicata in `references/search-syntax.md`.

## 2026-08-09 (rework esempi README)

- **README riscritto con esempi verificati live** (sezione "Esempi verificati", 11 scenari): ogni comando eseguito contro il catalogo reale il 2026-08-09, URL controllati con HTTP, output citati verbatim. Stato aggiornato a v2.0.
- **Audit degli esempi precedenti**: 2 URL su 8 morti — WMS ortofoto Provincia di Lodi (`sdi.provincia.lodi.it`, DNS ok ma TCP down a 2 tentativi) e WFS Regione Basilicata (`rsdi.regione.basilicata.it`, idem) → sostituiti con endpoint verificati 200 (Lombardia Ortofoto 2024, Sardegna, Piemonte mapproxy; WFS ARPA Veneto + ISPRA).
- **Numeri magici invecchiati**: Lombardia 430→438, edificato Bologna 40→44, frane open data 259→268 (catalogo cresce) → nel nuovo README i totali sono quelli del giorno di verifica, con nota esplicita.
- **Nuovi esempi wow verificati**: record → WFS → `ogr2ogr` GPKG in 2.2s (ARPA Veneto, 585 KB); sweep 108 WMS unici tema Idrografia in 10s; comune → 4 dataset CMBO con email contatto; footprint GeoJSON QGIS-ready.
- Nota onesta documentata: l'endpoint ARPA Veneto è catalogato in `http` e risponde con redirect a `https` (per questo `resources` senza `--no-check` dà 301, non 200 — `ogr2ogr` lo segue da solo).

## 2026-08-09 (valutazione utilità per figure professionali)

- **Valutazione v2.0.0 con verifica live contro l'API reale** in `docs/evaluation-v2.0.0.md`, scenari per tecnico GIS, analista spaziale e ufficio comunale. Esito: ottimo per GIS e analista, buono con attrito per il comune.
- Punto debole principale confermato dal vivo: **la ricerca per ente**. `apiso_OrganizationName_txt:"Comune di Bologna"` → 0 (testo analizzato), `EnteResponsabile_s` e prefisso IPA `c_a944` → 0 (comune non indicizzato con quei nomi), wildcard su `contact_organizations_s` → over-match. Percorso robusto per il comune: `AmbitoTerritoriale_s:Locale` + `--bbox` (15 record per l'area di Bologna vs 2789 con solo bbox).
- Verifiche live di conferma: filtro `--time` combinato (42 = atteso), `resources` con status 200 e probe HEAD, CSV `--profile qgis` pronto per QGIS, `footprints` GeoJSON valido, XML ISO 19139 valido, 5000 record `compact` in 36s, sort invalido → HTTP 500 con messaggio minimo (non traceback). 99/99 test verdi.
- Nuove proposte in `docs/future-ideas.md`: flag `--org`/`--suggest-org`, zero-risultati e sort invalido parlanti, `resources` in batch con latenza, tabella `--wide`.

## 2026-08-09 (release 2.0.0)

- **`--profile` era una trappola silenziosa**: `openrndt search --profile gis` stampava JSON, perché il preset di colonne vale solo per `table`/`csv` e `--format` è globale (va prima del sottocomando). Nessun errore, nessun avviso: l'opzione veniva semplicemente ignorata. Ora `--profile` senza `--format` esplicito attiva da solo `table`, e con `--format json|compact` espliciti la CLI dice su stderr che il preset non si applica.
- Il meccanismo è `output.set_mode(mode, explicit=...)`: il default `json` è marcato non-esplicito, così i comandi possono sovrascriverlo senza sovrascrivere una scelta dell'utente. Stessa distinzione su `--profile`, che passa a default `None` per separare «non passato» da `--profile default`.

## 2026-08-09 (release 1.1.0)

- **Rilasciata la 1.1.0**: comandi `resources` e `footprints`, profili `--profile gis|qgis`, filtri temporali `--updated-*`/`--published-*`, alias CRS per la bbox, flag `--version`. PR #12 e #13.
- **`resources` dichiarava rotti endpoint funzionanti**, sul suo stesso esempio di documentazione: il fallback a `GET` era limitato a `405/501`, ma i WMS/WFS reali rifiutano `HEAD` con 403/500 pur rispondendo 200 a `GET` (verificato su `age:D_E973_MARSAGLIA`, entrambe le risorse davano `ok=false`). Ora qualunque `4xx/5xx` viene riverificato in streaming senza scaricare il body. Difetto trovato da noi, non dai reviewer.
- **La versione aveva tre punti allineati a mano e uno era già disallineato**: pacchetto a 1.0.0, `USER_AGENT` fermo a `openrndt/0.1` dalla release precedente. Ora `_version.py` legge i metadati della distribuzione: `pyproject.toml` è l'unico punto da alzare, e `tests/test_version.py` impedisce il ritorno della deriva.
- **Hardening del check risorse** dopo sei giri di review automatica: allowlist di schema, blocco degli indirizzi non pubblicamente instradabili (incluso il CGNAT `100.64.0.0/10`, che sfuggiva a `is_private`/`is_reserved`), fail-closed quando il DNS non risolve, redirect non seguiti. **Declinato il pinning DNS**: chiude una finestra TOCTOU reale ma romperebbe il routing per nome sugli endpoint che lo strumento esiste per verificare — il reviewer ha ritirato il rilievo.
- **Un test faceva risoluzione DNS reale** (`test_cli_resources_json_with_check` verso `*.agenziaentrate.gov.it`), contro la regola «nessuna chiamata di rete nei test». Ora `conftest.py` stubba `getaddrinfo` per tutta la suite.
- Aggiunti in locale (non versionati, `.claude/` è gitignored): hook di lint+mypy sugli edit, hook che avvisa quando `src/` cambia senza `knowledge/` e `LOG.md`, skill `/release`, subagent `rndt-api-verifier`.

## 2026-07-27 (verifica post-email RNDT)

- **Riverificati live i 6 punti dell'email a info@rndt.gov.it (18/07): nessuno risolto.** (1) checkbox «Considera valori vuoti»: stesso JS inline (AND dei 3 range 1900–2100), ancora spuntata di default; (2) `sort=apiso_PublicationDate_dt:desc|asc` ancora ignorato (`apiso_Modified_dt` ok); (3) CSW: esempio §2.2.1 → 0 record e `numberOfRecordsMatched="[object Object]"`, GetDomain ancora `false`; (4) link `alternate` ancora su `192.168.3.34:8080` (anche OpenSearch nel GetCapabilities); (5) `dataCategory` ancora no-op (23.650 = totale); (6) nessun campo licenza normalizzato, conteggi CC invariati a meno dei nuovi record.
- Catalogo cresciuto da 23.632 a 23.650 record.

- **Ispezione del frontend ufficiale** (Ricerca Dettagliata) con `agent-browser` (cattura network/HAR headed). Riscritti `tmp/bugs-incoerenze.md` e `tmp/proposte-rndt.md` con le prove di oggi.
- **Correzione importante**: `apiso_PublicationDate_dt` **esiste** (8.402/23.632 record) ed è **filtrabile** via `q=…:[range]`, ma **non ordinabile**. Contraddice la nota precedente ("campo inesistente"): corretti `knowledge/api/known-issues.md` e issue #4. Il *filtro* per data di pubblicazione del metadato si può; l'*ordinamento* no.
- **Solo `title` e `apiso_Modified_dt` sono ordinabili** (confermato indipendentemente dal menu "ORDINA PER" del portale, che offre solo quei due). Ignorati `orderBy=`, `searchText=`, `after/before` (parametri nativi Esri che il frontend costruisce ma l'endpoint pubblico non onora).
- **Bug nuovo → issue #9**: la Ricerca Dettagliata mette in AND tutti e 3 i campi data quando ne filtri uno solo; "Considera valori vuoti" non funziona (campo assente non matcha `[1900 TO 2100]`). "incendi creati dal 2024 a oggi" → portale 0, reali 15.
- **Campo licenza incoerente**: `isOpendata` a volte `null` con la licenza solo in `apiso_OtherConstraints_s` (tutti i dataset AIB del MASE) → `isOpendata:*` perde open data reali. Aggiunto a issue #8.
- Riconfermati live #2 (IP interno 192.168.3.34, anche nei link export della UI ufficiale), #5 (CSW SortBy ignorato).
- Contatti supporto RNDT trovati: `info@rndt.gov.it`, Skype `rndt.help`.

## 2026-07-17 (skill audit)

- **Audit live della skill `rndt-explorer`** (comandi eseguiti contro l'API reale). Esito: struttura a 4 fasi solida, 4 punti stale corretti:
  - `workflows.md` #3/#4 usavano `--sort dateDescending` (che NON ordina, riconfermato live) → sostituito con `apiso_Modified_dt:desc` + warning.
  - `workflows.md` citava `apiso_PublicationDate_dt` → campo inesistente (verificato su record reale), rimosso; lista campi data corretta.
  - **Scoperta: il sort su `title` ora funziona** (`title:asc` ordina alfabeticamente) — l'API è cambiata rispetto a maggio-giugno, quando dava "Fielddata is disabled". Aggiornati `search-syntax.md`, `codelists.py` (commento), `knowledge/api/known-issues.md`. I campi garantiti sortable restano `_s`/`_dt`/`_i`.
  - `output-formats.md` non menzionava `compact` → aggiunta sezione dedicata (incl. `resources: []` → serve `get`).
  - SKILL.md: frontmatter v0.1→1.0, installazione da PyPI in compatibility, opzioni globali `--timeout`/`--base-url`.
  - **Nuovo workflow 7 per data journalist** (verificato end-to-end live su record ISPRA "Popolazione rischio alluvioni"): compact+isOpendata → `search --id` per link con dctype → `get` per licenza/ente/data (citazione fonte) → `ogr2ogr` dal WFS. Note oneste: enclosure raro, `isOpendata` a volte generico, download spesso dietro portali regionali.
  - Sanity numbers aggiornati al 2026-07-17 (catalogo 23.580→23.632).
  - Aggiunti `apiso_CRS`, `apiso_Format_s`, `isOpendata` ai campi utili di `search-syntax.md` (per operatori GIS).
- 55/55 test, ruff e mypy verdi (unica modifica codice: commento in `codelists.py`).

## 2026-07-17

- **Valutazione readiness produzione v0.1.0** in `docs/evaluation-v0.1.0.md`: codice production-grade, gap tutti infrastrutturali (no CI, no mypy, metadata PyPI incompleti, manca `py.typed` e CHANGELOG). Roadmap verso v1.0 inclusa.
- **Knowledge bundle OKF** in `knowledge/`: documentazione del progetto in Open Knowledge Format (markdown + frontmatter YAML, leggibile da umani e agenti). 18 file: project, architecture, skill, cli/ (search, get, discover), library/, api/ (endpoint + bug noti verificati live), conventions/ (errori, output, testing). Validato conforme OKF v0.1 (frontmatter `type`, cross-link integri).
- **`py.typed`** (PEP 561) aggiunto in `src/openrndt/`: verificato presente nel wheel dopo `uv build` senza bisogno di config aggiuntiva (`uv_build` lo include automaticamente). 38/38 test verdi. Primo punto della roadmap v1.0 in `docs/evaluation-v0.1.0.md`.
- **`mypy --strict` pulito** (secondo punto roadmap): aggiunto al gruppo dev, config `[tool.mypy]` in `pyproject.toml`. 5 fix reali: `discover()` in `cli.py` riusava la variabile `section` con due tipi diversi (rinominata `values`); `dict` senza type-arg in `client.py`; 3 `no-any-return` (`response.json()` non annotato) in `search.py`/`item.py`, risolti annotando la variabile o con `cast`. 38/38 test e ruff ancora verdi.
- **CI GitHub Actions** (terzo punto roadmap): `.github/workflows/ci.yml`, matrice Python 3.12/3.13, step `uv sync --locked` → `ruff check` → `mypy` → `pytest -v` su push/PR verso main. Sequenza verificata localmente prima del commit.
- **Metadata `[project.urls]`** (quarto punto): aggiunti `Repository`/`Issues` verso `github.com/ondata/openrndt`; rinominati i link RNDT (`RNDT Portal`/`RNDT REST API`) per chiarire che non sono il repo del codice.
- **README: installazione da PyPI** (quinto punto): sezione dedicata con `uv tool install openrndt`/`uvx`, nota onesta che il package non è ancora pubblicato; installazione locale riorganizzata in sezioni "Da locale" / "Per sviluppo".
- **`--timeout` configurabile in CLI** (sesto punto): nuova opzione globale, stesso pattern di `--base-url` (override in `config.py`: `get_timeout()`/`set_timeout()`, usato come default da `client.rndt_request()`). Verificato live: `--timeout 0.5` contro un IP non instradabile fallisce in ~1.5s con messaggio leggibile ed exit 1 (no traceback), invece dei ~90s del default. 38/38 test, ruff e mypy verdi.
- **v1.0.0 pubblicata** (ottavo punto, completo): `CHANGELOG.md`, bump versione, classifier PyPI `3 - Alpha` → `5 - Production/Stable`. Commit `08ecc36` pushato su `main`, tag annotato `v1.0.0` pushato. `uv build` + `twine check` PASSED, poi `uv publish` (token da `~/.pypirc`, dry-run prima del reale). **openrndt 1.0.0 è live su PyPI**: <https://pypi.org/project/openrndt/>. Verificato live: `uvx --from openrndt==1.0.0 openrndt --help` funziona da installazione pubblica pulita.
- **Coverage 89%→99%** (settimo punto) e **bug reale trovato nel farlo**: `--format <valore-invalido>` produceva un traceback completo (verificato live) — violava il principio cardine "mai uno stack trace". Fix: `ValueError` di `output.set_mode()` ora catturato nel callback `_root` di `cli.py` → messaggio leggibile + exit 2. +17 test: `tests/test_output.py` nuovo (rami table/csv irraggiungibili dalla CLI, testati chiamando `output.emit()` direttamente); percorsi di successo mai testati a livello CLI (`get` default json, `get --html`, `get --format table`, `discover` in table); `search --format compact` zero risultati; payload di risposta non-dict; parametro `--modified`; `keywords_s` come stringa singola; download senza `dctype`. Aggiunto `pytest-cov` (dev) e fixture di reset per `output_mode`/`timeout` in `conftest.py` (stesso pattern di `_reset_base_url`). Coverage residua (99%, righe 230/234 di `cli.py`): solo `main()`/`__main__` boilerplate. 55/55 test, ruff e mypy verdi.

## 2026-06-11

- **Nuovo formato `--format compact` (NDJSON per agenti).** Quarto formato di output per `search`: una riga JSON per record con i soli campi ad alto segnale (`id`, `title`, `org`, `type`, `category`, `updated`, `resources`). Pensato per far scremare molti risultati a basso consumo di token prima del `get`. Spunto dal progetto Copernicus-Services-Products-Metadata (rendering sintetico dei risultati; lì *prima* della ricerca perché catalogo locale, qui *dopo* perché catalogo remoto).
  - Libreria: `compact_results(payload)` in `search.py` — `org` da `apiso_OrganizationName_txt` (fallback `author.name`), `category` da `apiso_TopicCategory_s` (fallback keyword ISO), `resources` = dctype dei `links` (escluse rappresentazioni del metadato), dedup+sort.
  - `output.py`: aggiunto mode `compact` + branch NDJSON. `get --format compact` rifiutato come csv (dettaglio non tabellare).
  - Test: +6 (4 libreria, 2 CLI). 37/37 verdi, ruff pulito.
  - Doc: README (formati + Per agenti AI), SKILL.md, `docs/future-ideas.md` con gli altri spunti Copernicus (rerank semantico, snapshot/cronologia CI, Parquet).
- **Verifica `--bbox`** (challenge utente): il filtro funziona (semantica overlaps; 485→21 record in Sicilia, 0 in oceano). Il rumore "Toscana sotto bbox Sicilia" è dovuto a record con bbox dichiarato errato (tutta Italia `6.6,35.5,18.5,47.1`) — problema di qualità nei metadati sorgente, non del filtro.
- **Fix review PR #7** (Copilot + Greptile): SKILL elenca anche `updated` tra i campi compact; help `--format` chiarisce che `compact` è solo per `search`; docstring `emit()` csv allineata (output vuoto, non errore); `_topic_category` ora cerca la categoria ISO sia in `keywords_s` sia in `categories` (prima saltava il fallback se `keywords_s` era popolato ma senza valori ISO) +1 test; `docs/future-ideas.md` marca il compact come implementato. 38/38 verdi.
- **Nuova reference skill `references/ogc-services.md`**: guida all'esplorazione dei servizi OGC (WMS/WFS/WCS/WMTS) linkati nel catalogo RNDT con GDAL/OGR a output JSON. Punti verificati: `gdalinfo`/`ogrinfo -json` danno solo Nome+Titolo (no `queryable`/abstract → solo nel GetCapabilities, che ha tutto), `gdallocationinfo` per GetFeatureInfo, `ogr2ogr` per download vettoriale. Esempio catasto AdE (layer `fabbricati`, non `BU.Building`; WFS senza fabbricati; 3 layer queryable). Linkata da Fase 4 della SKILL.

## 2026-06-10 (continua)

- **README: sezione "Esempi di conversazione con un'AI"** per utenti GIS desktop (non CLI). 7 scenari conversation-first (domanda in linguaggio naturale → comando openrndt leggibile → URL WMS/WFS da incollare in QGIS), tutti con risultati RNDT reali e verificati live: uso suolo Emilia-Romagna (WMS getCapabilities testato 200), catasto Piemonte, ortofoto (Sardegna/Lodi/Piemonte), reticolo idrografico WFS (ISPRA/ARPA Veneto/Basilicata), 430 dataset Regione Lombardia, bbox area Bologna (40, framing onesto "sovrapposizione"), 259 frane open data. Niente jq mostrato, niente link con IP interni (bug issue #2).
- **Fix review PR #6** (Greptile + Copilot). Risolto il tema centrale: `json.JSONDecodeError` (sottoclasse di `ValueError`) su risposte 2xx con body non-JSON.
  - `get`: ora cattura `json.JSONDecodeError` → messaggio leggibile + exit 1 (prima → traceback, violava "mai stack trace").
  - `search`: separato `JSONDecodeError` (exit 1, "risposta inattesa") da `ValueError` di validazione parametri (exit 2), che prima collassavano sullo stesso exit 2 fuorviante.
  - `_http_error()`: fallback a `config.get_base_url()` quando `exc.request` manca (es. `ConnectError` senza request) → messaggio sempre self-contained; tipato `-> NoReturn`.
  - Doc: README chiarisce che i retry valgono per timeout/5xx, non per `ConnectError`; docstring `search()`/`get_item()` documentano `json.JSONDecodeError`. Rimossa fixture inutile in un test. 31/31 verdi (+2: malformed-json su search e get).

- **Allineamento ai principi "CLI per orchestrazione LLM" di opensdmx.** Fix di principio (errori leggibili, niente stack trace) + doc:
  - `cli.py`: errori di rete (`ConnectError`, `TimeoutException` dopo retry) e HTTP ora catturati via `httpx.HTTPError` → messaggio leggibile su stderr + exit 1, **niente più traceback** (era il gap principale: porta morta/no-network dumpava lo stack). Helper `_http_error()` condiviso da `search`/`get`.
  - `get --format csv` (dettaglio non tabellare) → messaggio esplicito + exit 1, **senza chiamata di rete**, invece di output vuoto silenzioso. `search` 0-risultati (csv/table) → avviso su stderr, exit 0. Rimosso anche l'exit 1 muto su payload non-dict.
  - Libreria: docstring di `search()`/`get_item()` documentano le eccezioni propagate (`httpx.HTTPError`); README sezione libreria + nuova sezione "Per agenti AI" con i principi di design.
  - `cli.py`: parametri fuori range (`--num` > 5000, `--start` < 1) ora catturano `ValueError` → messaggio leggibile + exit 2 (parametri non validi), niente traceback.
  - Decisione: **no** rename `--format`→`--output` (parità solo ortografica, contraddice CLAUDE.md) e **no** comando `which` (scope creep). 29/29 test verdi (+5: connect-error/no-traceback, csv-zero-results, get-csv-non-tabellare, invalid-num/no-traceback).

- PR #3 mergiata su main (`docs/sort-csw-limitations`). Issue aperte: #4 (data pubblicazione non ordinabile via REST), #5 (CSW `SortBy` ignorato, non conforme INSPIRE Discovery Services v3.1). Installazione CLI globale aggiornata.
- **Scoperta sort** (verificata live, cross-validata su endpoint test Esri): il sort reale è `campo:asc|desc` su campi sortable (`_s`/`_dt`/`_i`); `dateDescending`/`dateAscending` documentati NON ordinano (ignorati). Campi `text` (`title` nudo) → errore ES "Fielddata is disabled". Nessun campo data-pubblicazione indicizzato: proxy = `apiso_Modified_dt:desc`.
- **Scoperta CSW**: `/csw` ignora del tutto `<ogc:SortBy>` (qualsiasi proprietà/direzione) → non conforme INSPIRE Technical Guidance Discovery Services v3.1.
- Allineati: `codelists.py` (SORT_VALUES + note campi data), `cli.py` (help `--sort`), `search.py` (docstring), `ref/rest-api-rndt.md` (note sort + CSW), skill `SKILL.md` + `search-syntax.md` (sezione Ordinamento + filtro ente robusto). 25/25 test verdi.
- Nota qualità dati: stesso ente con molte varianti di `apiso_OrganizationName_txt` → filtrare per `EnteResponsabile_s` o prefisso id (codice IPA ente capofila).
- Skill `rndt-explorer` aggiornata con nuovi campi Lucene scoperti live: `apiso_OrganizationName_txt`, `EnteResponsabile_s`, `apiso_Type_s`, `PuntoDiContattoEmail_s`, `PuntoDiContatto_s`, `PuntoDiContattoSitoWeb_s`.
- Documentata distinzione `author.name` (username sistema) vs `apiso_OrganizationName_txt` (nome ente).
- Documentato codice IPA ricavabile dal prefisso dell'`id` (es. `r_sicili:uuid` → IPA `r_sicili`).
- Aggiunti esempi query live per filtro per organizzazione, ordinamento per data, filtro per tipo risorsa.
- PR #1 mergiata su main (`fix/item-not-found-and-internal-links`).
- Issue #2 aperta: segnalazione bug RNDT (link IP interno + 500/501 per ID inesistente).

## 2026-06-10

- Valutazione qualità (v0.1.0): punteggi per dimensione in `docs/evaluation.md`.
- Fix stale assertion in `tests/test_discover.py`: aggiunto `lucene_fields` al set atteso.
- Rimossa dipendenza `pydantic` da `pyproject.toml` (non usata).
- Rimossa variabile morta `last_exc` in `client.py` (ruff F841).
- Gestione `httpx.HTTPStatusError` in `cli.py` (search + get): messaggio leggibile su stderr invece di traceback.
- Sostituito `assert isinstance(payload, dict)` con check esplicito in `cli.py`.
- Nuovi test retry in `tests/test_retry.py`: 503→200 (retry ok) e 3×503 (propaga errore). Totale: 21/21 test verdi.

## 2026-05-27

- Bootstrap progetto: `pyproject.toml`, `LICENSE` MIT, `.python-version` 3.12, `.gitignore`, `CLAUDE.md`, `LOG.md`.
- PRD ripensato e formalizzato (v0.1 read-only: `search`, `get`, `discover`).
- Endpoint produzione confermato live: `https://geodati.gov.it/RNDT/rest/metadata/search` → HTTP 200, 23.580 record nel catalogo.
- Endpoint `item/{id}` JSON/XML/HTML verificati live (HTTP 200).
- Cartella `ref/` con spec `gpt_api.json` (sito di test Esri Geoportal Server) e doc estratta dalla pagina ufficiale.
- CLI implementata: `src/openrndt/{config,client,codelists,search,item,output,cli}.py` + entry point Typer `openrndt`. Installata in editable nel venv `~/.venvs/data`.
- 19 test pytest verdi (HTTP mockato con `respx`, fixture reali in `tests/fixtures/`).
- Skill `rndt-explorer` con SKILL.md (137 righe, 4 fasi) + 5 references verticali (categories, search-syntax, result-structure, output-formats, workflows).
- **Bug RNDT scoperti durante validazione** (documentati in `tmp/bugs-incoerenze.md`):
  1. Parametro `dataCategory` documentato non filtra — fix: traduzione automatica `--data-category` → `q=keywords_s:VAL` lato CLI.
  2. Combinazione `time` + `q` su campo specifico → 0 risultati.
  3. Campo `updated` riflette reindex catalogo, non data dataset.
  4. `total` di tipo variabile (int o `{value, relation}`).
  5. Confusione `geodati.gov.it` vs `gpt.geocloud.com`.
- Piano completo in `/home/aborruso/.claude/plans/studia-questo-prd-md-mettilo-partitioned-papert.md`.
- Installazione globale via `uv tool install /home/aborruso/git/idee/openrndt/` → binario in `~/.local/bin/openrndt` (venv isolato). Aggiornamento: `uv tool install --reinstall <path>`. Disinstallazione: `uv tool uninstall openrndt`.
