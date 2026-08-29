# Valutazione openrndt 3.0.0 - idoneità per tecnici GIS, giornalisti e ricercatori

Data: 2026-08-29 · Versione valutata: 3.0.0 (installata da PyPI) · Metodo: esecuzione live contro l'API RNDT, con scenari delle tre figure, fino al file in mano quando lo scenario lo prevedeva.

Questa valutazione guarda l'adozione da parte di persone. Il taglio agentico (openrndt come backend di una CLI guidata da un agente) è già coperto da `docs/evaluation-v3.0.0.md` e non viene rifatto qui: dove serve, lo cito.

## Benestare al lancio del tool

Sì. Il tool può essere annunciato pubblicamente così com'è.

Regge la prova che conta per tutti e tre i profili: dal titolo di un dataset al file aperto in QGIS, senza uscire dal terminale e senza conoscere né l'API né la sintassi Lucene. Verificato oggi: dal record `arpa_ve:Stato_Chimico_Fiumi_DGR_3_2022` al GeoPackage del layer che quel record descrive (`geonode:Stato_Chimico_Fiumi_DGR_3_2022`, 867 punti, 536 KB) in circa 3,3 secondi, 0,6 di openrndt per gli endpoint e 2,7 di `ogr2ogr` sul WFS. Con un passaggio manuale in mezzo, descritto più sotto. L'esempio 6 del README, rifatto senza modifiche, dà 107 endpoint WMS unici in 11 secondi contro i 108 dichiarati: il catalogo si è mosso di un record, la promessa regge.

Il benestare non è condizionato, ma una cosa andava fatta prima o subito dopo l'annuncio, ed era al primo posto dei punti deboli: una bbox scritta male non veniva validata e restituiva l'intero catalogo con exit code 0. Su un pubblico di giornalisti è il difetto con la conseguenza peggiore, perché produce un numero plausibile e sbagliato. È stata corretta lo stesso giorno, insieme ai punti 2 e 3: vedi la nota qui sotto.

> **Aggiornamento del 2026-08-29, a valutazione conclusa.** Le prime tre debolezze e le prime tre proposte sono state implementate: la bbox è validata lato client con uscita 2 prima della chiamata di rete, e `open`, `license` e `url` sono ora campi di `compact`, `csv`, `table` e delle proprietà di `footprints`. Il resto di questo documento descrive la 3.0.0 pubblicata su PyPI, che è quella che si ottiene oggi con `uvx openrndt`: le tre correzioni usciranno con la 3.1.0. L'annuncio va quindi dopo quel rilascio, altrimenti i materiali di lancio mostrerebbero un output che chi prova non vede.

## Come annunciarlo e cosa realizzare

### Il messaggio, diverso per ciascun pubblico

Non esiste un annuncio unico che funzioni per le tre figure, perché il problema che risolve non è lo stesso.

Ai tecnici GIS si dice che il catalogo nazionale diventa un layer in QGIS senza passare dal portale: si cerca per tema e area, si ottengono gli endpoint, si scarica. È il pubblico che capisce subito e che porta i primi utenti veri.

Ai giornalisti si dice un'altra cosa: che si può chiedere cosa pubblica un ente sul proprio territorio, con quale licenza e con quale link citabile, e ottenere una risposta in mezzo secondo invece che navigando un portale. Qui il messaggio non è tecnico, è una domanda che si può finalmente fare.

Ai ricercatori si dice che si può interrogare la copertura di un'area di studio, filtrare per scala e per data della scheda, ed esportare i footprint come GeoJSON per ragionare sulla completezza del catalogo.

### I materiali

- **Un post lungo con un caso reale**, sul sito di ondata: una domanda pubblica, i comandi che la risolvono, il file ottenuto e la mappa o il grafico finale. È il pezzo che regge tutto il resto e a cui gli altri annunci rimandano.
- **Una registrazione del terminale** (asciinema o GIF) del percorso più corto, dalla ricerca al layer aperto. Pochi secondi reali convincono più di una descrizione.
- **Tre esempi brevi, uno per pubblico**, ciascuno di tre comandi, da riusare come corpo dei post sui canali verticali.
- **La skill `rndt-explorer` annunciata separatamente**, per chi usa un assistente e non vuole imparare la CLI: è un pubblico diverso e un annuncio diverso. Prima di distribuirla va allineato `metadata.version` alla versione della CLI, visto che esistono copie omonime non sincronizzate e il caricamento per nome ha già risolto sulla copia sbagliata (nota metodologica di `evaluation-v3.0.0.md`).
- **Una pagina di ingresso nel README** che smisti verso i tre percorsi, invece dell'unica sequenza di esempi che c'è oggi.

### I canali

Il pubblico GIS sta su GFOSS.it e nelle liste OSGeo italiane. Quello di giornalisti e civic hacker su Spaghetti Open Data, lista e gruppo Telegram. Il canale ondata è la casa del progetto e il punto da cui far partire tutto. LinkedIn e Mastodon coprono il resto, con il post lungo come destinazione.

Vale la pena segnalarlo anche a chi gestisce il RNDT in AgID, e conviene farlo con attenzione: il progetto documenta e aggira difetti verificati della loro API, e presentarlo come uno strumento che rende più usabile il catalogo, con le anomalie allegate come contributo, è diverso dal presentarlo come una critica.

### Cosa non promettere

Che nel catalogo ci sia tutto. Il tool restituisce ciò che gli enti hanno pubblicato, e su un tema come l'uso del suolo quasi due terzi delle schede non linkano alcuna risorsa. Dichiararlo nell'annuncio evita che il primo tentativo a vuoto venga attribuito allo strumento, e va detto insieme alla riga che chiarisce che il progetto è indipendente e non è un prodotto AgID.

### Per chi prova subito

Una riga sola, e non è un dettaglio secondario per un pubblico non sviluppatore: si prova senza installare nulla, con `uvx openrndt search --q "frane" --profile gis --num 10`, e a freddo la prima risposta arriva in poco più di mezzo secondo. Nessuna chiave, nessuna registrazione, nessuna configurazione.

## Punti di forza

- **Il percorso arriva fino al dato, non si ferma al metadato.** `resources` estrae gli endpoint e li verifica davvero, con `ok`, `status_code` e `latency_ms`: sul record ARPA Veneto, WMS e WFS rispondono 200 in circa un secondo, e da lì `ogr2ogr` porta a casa il file. È la differenza fra un catalogo consultabile e un catalogo usabile.
- **Velocità che cambia il modo di lavorare.** Una ricerca sta sotto il mezzo secondo, 500 record in 6 secondi, la discovery delle codelist è offline e istantanea. Si può esplorare per tentativi, che è esattamente come si cerca quando non si sa ancora cosa si cerca.
- **Gli zero risultati non sono un vicolo cieco.** Cercando "consumo di suolo" per il Comune di Palermo, la CLI risponde 0 e spiega che nessun ente in catalogo somiglia a quel nome, che l'ente potrebbe non pubblicare in proprio, e suggerisce la ricerca per territorio. Per un giornalista è la differenza fra abbandonare e trovare il dato sotto un altro ente.
- **I formati sono calibrati sull'uso, non sul gusto.** `compact` costa due ordini di grandezza meno di `json` (1,4 KB contro 178 KB su 5 record) e resta leggibile a occhio; `csv` apre in un foglio di calcolo senza conversioni; `footprints` produce un GeoJSON che `ogrinfo` legge senza obiezioni e QGIS apre con un doppio clic.
- **La documentazione dice la verità sui difetti della fonte.** Che `dataCategory` non filtri, che `dateDescending` non ordini, che due date con lo stesso nome siano cose diverse: sono scritti, verificati e datati. Per un ricercatore che deve giustificare un metodo, un tool che documenta i limiti della fonte vale più di uno che li nasconde.

## Punti di debolezza che non dipendono dalla fonte

- **La bbox non è validata e il fallimento è silenzioso.** `--bbox "non,valido"` restituisce `total: 23738`, cioè il catalogo intero, con exit code 0; `--bbox "12,45,11"`, tre valori invece di quattro, si comporta allo stesso modo. Una bbox invertita (`12,45,11,44`) esce invece con HTTP 500. È l'API a ignorare il parametro malformato, ma la validazione client manca ed è la stessa raccomandazione già scritta in `evaluation-v3.0.0.md` del 9 agosto, ancora non implementata. Per chi filtra su una provincia e pubblica un conteggio, il risultato è un numero nazionale spacciato per locale.
- **La licenza non compare in nessun output sintetico.** Il dato esiste nel metadato (`isOpendata`, `apiso_ConditionApplyingToAccessAndUse_txt`, che su un record Toscana dice "liberamente accessibile e usabile con licenza CC BY") ma non è colonna né in `table`, né in `csv`, né in `compact`, né nelle proprietà di `footprints`. Per chi deve decidere se può ripubblicare, è il campo decisivo, e oggi richiede un `get` per record più una query jq che bisogna sapere scrivere.
- **Manca il permalink citabile negli output sintetici.** L'URL pubblico della scheda esiste, sta nei `links` come `rel: alternate` di tipo `text/html` e risponde 200, ma per averlo bisogna passare dal JSON grezzo. Un ricercatore che cita una fonte e un giornalista che linka la scheda ne hanno bisogno in ogni riga di output.
- **Le stesse cose hanno nomi diversi fra un comando e l'altro.** In `search` i collegamenti sono `links[]` con chiavi `href`, `rel`, `dctype`; in `resources` sono `resources[]` con chiavi `url`, `type`. Chi scrive una pipeline jq inciampa nel passaggio da un comando all'altro, ed è successo anche in questa valutazione.
- **La tabella è dura da leggere per chi non è del mestiere.** In un terminale standard da 80 colonne, il profilo di default spezza l'identificatore su cinque righe e riduce il titolo a una colonna di dodici caratteri; il profilo `gis`, con nove colonne, resta scomodo anche a 120. Manca un preset a poche colonne per la lettura umana, con l'identificatore troncato o spostato in fondo. Da notare che il formato predefinito è `json`: il primo comando che una persona lancia senza opzioni le riversa in terminale 51 KB per un solo record.
- **L'endpoint da solo non basta: il nome del layer va cercato a mano.** Gli URL che `resources` restituisce sono `GetCapabilities` di tutto il server, non del layer del record. Su un GeoServer con centinaia di layer, come quello di ARPA Veneto, l'elenco è lungo e trovare quello giusto richiede di leggerlo per intero (in questa valutazione, due tentativi e un timeout prima di individuarlo). Il nome però c'è nel metadato: il primo link del record è `https://gaia.arpa.veneto.it/layers/geonode_data:geonode:Stato_Chimico_Fiumi_DGR_3_2022`, da cui il layer si ricava. La CLI non lo espone.

- **Nessun modo di chiedere solo ciò che è fruibile.** Su 200 record del tema "uso del suolo", 126 non hanno alcuna risorsa collegata. Che il catalogo sia così dipende dalla fonte, ma la CLI non offre un filtro per escluderli: la scrematura si fa a valle, con jq su `compact`, e chi non conosce jq scorre a mano.

### Cosa non conto contro il tool

La copertura del catalogo è quella che è: molti comuni non pubblicano in proprio, le risorse scaricabili sono una minoranza (su quei 200 record, zero download diretti e 48 WMS), diverse schede dichiarano una bbox mondiale che rende il footprint inutilizzabile, e alcuni endpoint catalogati rispondono 500 (il WMS del Comune di Capannori, oggi). Sono difetti dei metadati, non dello strumento. Il punto a favore di openrndt è semmai che li rende visibili in un colpo d'occhio, cosa che il portale non fa.

## Proposte

In ordine di rapporto fra valore e costo.

1. **Validare la bbox lato client**, con lo stesso schema già usato per le date: quattro valori numerici, longitudini fra -180 e 180, latitudini fra -90 e 90, `xmin < xmax`, `ymin < ymax`. Errore con exit code 2 prima della chiamata di rete. Chiude l'unico difetto capace di produrre numeri sbagliati senza avvisare.
2. **Aggiungere `license` agli output sintetici** (`compact`, `csv`, `table`, proprietà di `footprints`), ricavata da `apiso_ConditionApplyingToAccessAndUse_txt` con `isOpendata` come indicatore. È il campo che apre l'uso del catalogo a chi pubblica.
3. **Aggiungere `url`**, il permalink della scheda, agli stessi output. Costa poco e rende ogni riga citabile.
4. **Un filtro per la fruibilità**, del tipo `--has-resources` con eventuale scelta del tipo (`--has-resources wfs,download`), applicato a valle dei risultati come già fa `compact` per il campo `resources`. Trasforma un catalogo di 23.738 schede in un elenco di cose che si possono aprire.
5. **Un preset di lettura umana** per `table`, con quattro o cinque colonne (titolo, ente, aggiornamento, risorse) e l'identificatore troncato. Da valutare se renderlo il comportamento predefinito quando lo standard output è un terminale, lasciando `json` quando l'output è rediretto: è il comportamento che un utente si aspetta e che oggi va chiesto esplicitamente.
6. **Uniformare i nomi dei campi** fra `search` e `resources`, mantenendo per una versione gli alias vecchi. Una rottura di contratto, quindi da programmare, non da fare di corsa.
7. **Esporre il nome del layer** in `resources`, quando è ricavabile dai link del record (il pattern `/layers/<workspace>:<layer>` di GeoNode è il caso più frequente). È il pezzo che oggi separa un endpoint da un comando `ogr2ogr` pronto, e senza di esso il percorso "dal metadato al file" resta artigianale.
8. **Segnalare le bbox sospette**, quando un record dichiara l'estensione del mondo intero: una nota su stderr in `footprints`, o una proprietà nel GeoJSON. Non corregge la fonte, ma evita che una mappa venga letta male.

I punti 2 e 3, presi insieme, sono ciò che sposta openrndt dal pubblico dei tecnici GIS a quello di giornalisti e ricercatori: senza licenza e senza link citabile, quei due profili devono comunque tornare sul portale, ed è lì che l'attrito li ferma.
