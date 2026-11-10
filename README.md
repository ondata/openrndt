[![PyPI version](https://img.shields.io/pypi/v/openrndt)](https://pypi.org/project/openrndt/)
[![GitHub](https://img.shields.io/badge/github-ondata%2Fopenrndt-blue?logo=github)](https://github.com/ondata/openrndt)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ondata/openrndt)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Newsletter](https://img.shields.io/badge/newsletter-ondata-FF6719?logo=substack)](https://ondata.substack.com/)

# openrndt

> **Nota:** strumento in evoluzione — aiutaci a migliorarlo [aprendo issue](https://github.com/ondata/openrndt/issues) o condividendo feedback.

CLI Python e libreria per accedere al **Repertorio Nazionale dei Dati Territoriali (RNDT)** —
pensata per essere orchestrata da un'AI.

**Il modo giusto di trovare dati territoriali con l'AI.** I modelli linguistici capiscono bene le domande, ma inventano nomi di dataset e URL di servizi WMS/WFS che non esistono. Il pattern corretto è usare l'AI per *comporre interrogazioni al catalogo ufficiale*, non per generare i riferimenti. openrndt è il layer di esecuzione di quel pattern: l'AI decide cosa cercare, openrndt interroga il RNDT e restituisce metadati e URL reali, verificabili.

> **Al meglio con un'AI.** openrndt funziona benissimo da solo, ma **dà il massimo se guidato da un agente AI**: la CLI è progettata per essere composta, interrogata e orchestrata passo passo. Per un'esperienza guidata — scoperta delle codelist, ricerca con filtri progressivi, dettaglio del metadato, risorse scaricabili — abbinala alla Agent Skill [`rndt-explorer`](https://github.com/ondata/openrndt/blob/main/skills/rndt-explorer/SKILL.md) inclusa in questo repo. I principi di design sono nella sezione [Per agenti AI](#per-agenti-ai).

> Stato: v3.x — read-only.

## Cos'è il RNDT

Il [Repertorio Nazionale dei Dati Territoriali](https://geodati.gov.it/geoportale/) è
il catalogo ufficiale italiano dei metadati geografici (ISO 19115/19139). Espone REST
API per cercare e scaricare i metadati.

## Cosa aggiunge la CLI al geoportale

Il [geoportale](https://geodati.gov.it/geoportale/ricerca-dettagliata) è pensato per consultare il catalogo a vista: ci si disegna un'area sulla mappa e si sfogliano le schede. openrndt lavora sullo stesso catalogo ed è pensata per l'uso da programma: conviene quando vuoi contare, esportare o ripetere una ricerca, o farla guidare da un agente. Le differenze sono di tre tipi, e in parte sono una questione di preferenze: noi troviamo più comoda la modalità machine-to-machine.

### Non disponibili nel modulo di ricerca del sito

| Cosa vuoi fare | Comando | Come funziona |
|---|---|---|
| Esportare i risultati | `openrndt --format csv search --q ortofoto --profile qgis --num 100`, `openrndt footprints --q ortofoto > riquadri.geojson` | JSON, CSV con le colonne pronte per QGIS, GeoJSON con i riquadri, fino a 5.000 schede per richiesta. |
| Leggere la licenza anche dai vincoli d'uso | `openrndt --format compact search --ipa r_lombar --q DUSAF --num 5` | Il campo `license` riporta anche la licenza dichiarata nel blocco INSPIRE delle condizioni d'uso. |

### Pronte qui, sul sito con la sintassi di ricerca

Il modulo del sito non ha un campo per queste ricerche, ma il suo campo di testo in modalità «Testo» accetta la sintassi di ricerca del catalogo. Chi la conosce può scrivere la query dell'ultima colonna e ottiene lo stesso numero di schede.

| Cosa vuoi fare | Comando | Nel campo di testo del sito |
|---|---|---|
| Trovare tutti i dati di un ente dal codice IPA, comprese tutte le grafie del nome e le schede senza ente responsabile | `openrndt search --ipa r_sardeg` | `apiso_Identifier_s:/[rR]_[sS][aA][rR][dD][eE][gG]:.*/`. Il codice scritto come testo semplice può non bastare, perché nel catalogo il prefisso è sia maiuscolo sia minuscolo: `r_sardeg` trova 590 schede su 766. |
| Trovare un ente da una parte del nome, varianti comprese, come «Regione Piemonte - A1601B» | `openrndt search --org "regione piemonte"` | `EnteResponsabile_s:/.*[rR][eE][gG][iI][oO][nN][eE] [pP][iI][eE][mM][oO][nN][tT][eE].*/` |
| Cercare un tema in tutte le forme presenti nel catalogo: nome italiano, inglese, codice e altre grafie | `openrndt search --inspire-theme hy` | `INSPIRETheme_s:("Idrografia" OR "Hydrography" OR "hy" OR "idrografia")`. Il filtro per temi del modulo cerca nome italiano e inglese. |

### Più comode da programma

| Cosa vuoi fare | Comando | Come funziona |
|---|---|---|
| Cercare per regione o comune | `openrndt discover --what ipa --match "comune di firenze"`, poi `openrndt search --ipa c_d612`; per area `openrndt search --q AmbitoTerritoriale_s:Locale --bbox 11.2,44.4,11.5,44.6` | A un agente basta nominare il territorio: trova il codice dell'ente o le coordinate e combina i filtri. Restringere all'ambito locale toglie le schede che coprono l'area solo perché dichiarano un riquadro più grande: nell'esempio, 61 contro 2.870. |
| Esplorare un gruppo di temi | `openrndt discover --what inspire_themes`, poi `openrndt search --inspire-cluster mare-atmosfera` | I 9 gruppi con i loro 34 temi in un albero consultabile offline, e un solo filtro per tutto il gruppo. |
| Sapere se i link di una scheda funzionano | `openrndt resources <id>` | Controlla in un colpo servizi e download, anche di più schede insieme. |
| Vedere i layer di un WMS o WMTS | `openrndt resources <id> --layers` | L'elenco dei layer come dati, ognuno con il link che lo apre sulla mappa in GeoLibre web. |
| Automatizzare | [libreria Python](#uso-come-libreria-python) e [skill per agenti AI](#per-agenti-ai) | Le stesse ricerche in uno script o guidate da un agente, con output strutturato e comandi ripetibili. |

## Agent quickstart

Incolla questo prompt nel tuo agente AI, senza bisogno di skill o server MCP: controlla cosa hai già, chiede conferma prima di installare ciò che manca e arriva a una prima ricerca reale nel catalogo.

```text
Aiutami a usare openrndt (https://github.com/ondata/openrndt), una CLI Python che interroga il Repertorio Nazionale dei Dati Territoriali (RNDT), il catalogo ufficiale italiano dei metadati geografici, e restituisce schede e URL reali di servizi WMS, WFS e download.

Procedi così:
1. Esegui `openrndt --version`. Se risponde 3.15.0 o successiva, la CLI è già installata: non chiedermi nulla e vai al punto 3.
2. Se manca o è più vecchia e l'ambiente lo permette, chiedimi conferma e installala con `uv tool install openrndt`, oppure aggiornala con `uv tool upgrade openrndt`. Se manca `uv`, chiedimi se installarlo seguendo https://docs.astral.sh/uv/getting-started/installation/ (serve Python 3.12 o successivo). Poi ripeti `openrndt --version`.
3. Leggi `openrndt --help`. È pensato per gli agenti, quindi usalo come guida principale e apri il `--help` di ogni comando prima di usarlo. `openrndt discover` elenca i valori validi dei filtri senza usare la rete.
4. Prima prova: ricava il codice dell'ente con `openrndt discover --what ipa --match torino` (atteso `c_l219`, Comune di Torino), poi fai una sola ricerca reale con `openrndt --format compact search --ipa c_l219 --q catasto --num 3` (attese tre righe JSON con `id` che inizia per `c_l219:` e `org` uguale a Comune di Torino). Mostrami titolo, ente e risorse (`resources`) di ogni riga.
5. Solo alla fine, in un unico messaggio, proponimi due o tre ricerche possibili a partire da questo risultato, chiedimi quali dati territoriali sto cercando e proponimi due extra facoltativi, se non li ho già: la skill `rndt-explorer`, che guida la ricerca passo passo (https://github.com/ondata/openrndt/tree/main/skills/rndt-explorer, da installare nel modo previsto dal tuo client), e GeoLibre, consigliato dal progetto per portare i dati su una mappa (https://github.com/ondata/openrndt/blob/main/README.md#vedere-i-dati-su-una-mappa-geolibre-consigliato). Non installare nessuno dei due senza il mio sì.

Regole:
- `--format` va prima del comando (`openrndt --format compact search ...`), altrimenti dà errore.
- Usa solo id, codici e URL restituiti dalla CLI: non inventarli e non completarli a memoria.
- `open: false` vuol dire solo che l'ente non ha dichiarato il dato come aperto in quel campo, non che sia chiuso.
- `updated` è la data della scheda, non del dato. La data del dato è `data_date` in `openrndt get <id>`: se manca, dimmi che non è nota.
- Per il resto segui https://github.com/ondata/openrndt/blob/main/skills/rndt-explorer/SKILL.md e https://github.com/ondata/openrndt/blob/main/README.md

Mostrami i comandi usati e i risultati reali, con la fonte, le date disponibili e i limiti. Se installazione, rete o esecuzione non sono disponibili, dimmi cosa è bloccato e dammi i comandi documentati da lanciare a mano. Non inventare risultati e non dire di aver eseguito ciò che non hai eseguito. Rispondimi nella mia lingua.
```

## Installazione

### Da PyPI

```bash
uv tool install openrndt
# oppure, senza installazione persistente:
uvx openrndt --help
```

### Da locale (per sviluppo o versioni non ancora pubblicate)

```bash
git clone https://github.com/ondata/openrndt.git
cd openrndt

# CLI globale: venv isolato, eseguibile in PATH
uv tool install .

# Aggiornamento dopo modifiche al codice
uv tool install --reinstall .

# Disinstallazione
uv tool uninstall openrndt
```

### Per sviluppo (modifiche con ricarica immediata)

```bash
git clone https://github.com/ondata/openrndt.git
cd openrndt
uv sync
uv run openrndt --help
```

## Uso

```bash
# Ricerca testuale
openrndt search --q "catasto" --num 5

# Più parole sono in AND (--q-mode any per l'OR, lucene per passare la sintassi Lucene intatta)
openrndt search --q "copertura del suolo" --num 5

# Filtro per bounding box (Piemonte sud)
openrndt search --q "cartografia" --bbox 7,44,8,45 --num 10

# Profilo GIS (campi essenziali). Senza --format l'output diventa una tabella
openrndt search --q "catasto" --profile gis --num 10

# Profilo QGIS (CSV con colonne URL servizi + bbox separata)
openrndt --format csv search --q "catasto" --profile qgis --num 10

# Cosa pubblica un ente: dal nome al codice IPA, poi il filtro
openrndt discover --what ipa --match torino
openrndt search --ipa c_l219 --num 10

# Filtri temporali avanzati (aggiornamento + pubblicazione)
openrndt search --q "catasto" --updated-from 2024-01-01 --published-from 2020-01-01 --num 10

# Export footprint bbox in GeoJSON (EPSG:4326)
openrndt footprints --q "catasto" --num 50 > footprints.geojson

# Per categoria tematica ISO 19115
openrndt search --data-category planningCadastre --num 5

# Per tema o cluster INSPIRE, in tutte le forme presenti nel catalogo (solo dataset e serie)
openrndt search --inspire-theme hy --num 5
openrndt search --inspire-cluster mare-atmosfera --ipa r_sardeg --num 5
openrndt discover --what inspire_themes

# Singolo metadato (documento normalizzato: contatto, bbox, lineage, risorse)
openrndt get age:D_E973_MARSAGLIA

# Lo stesso metadato come busta Elasticsearch grezza
openrndt get age:D_E973_MARSAGLIA --raw

# Estrai e verifica endpoint WMS/WFS/download di un metadato
openrndt resources age:D_E973_MARSAGLIA

# Layer di ogni WMS e WMTS, ognuno con un geolibre_url che lo apre già sulla mappa
openrndt resources r_emiro:2022-03-11T113115 --layers

# Il link a GeoLibre web con il layer della scheda già sulla mappa
openrndt get agea:OI:ORTOIMMAGINI:m004 | jq -r .geolibre_map_url

# XML ISO 19139 grezzo
openrndt get age:D_E973_MARSAGLIA --xml > meta.xml

# Codelist disponibili (no rete)
openrndt discover
```

Dalla 3.3.0 `get` con `--format json` (il default) non restituisce più la sola
busta Elasticsearch: costruisce un documento con lo stesso vocabolario delle
risposte di `search` (`id`, `title`, `org`, `type`, `category`, `updated`,
`indexed`, `open`, `license`, `url`, `geolibre_url`) più i campi che servono a usare davvero la
scheda: `data_date` (la data del **dato**, non della scheda), `contact`
(`{name, email, website}` del punto di contatto designato), `bbox`
(`{xmin, ymin, xmax, ymax}`), `lineage` e `resources` (le risorse fruibili già
tipizzate e deduplicate, come `resources --no-check`).

La modifica è additiva: `_source` e i flag della busta (`_index`, `_id`,
`_version`, `found`, …) restano in coda con gli stessi valori di prima, quindi
ogni `jq` scritto per le versioni precedenti continua a funzionare. `--raw`
restituisce la sola busta, com'era ante 3.3.0.

```bash
openrndt get age:D_E973_MARSAGLIA | jq '{data_date, email: .contact.email, bbox}'
```

La bbox viene controllata prima della chiamata: quattro valori numerici, longitudini
fra -180 e 180, latitudini fra -90 e 90, `xmin < xmax` e `ymin < ymax`. Una bbox
malformata esce con codice 2 e un messaggio esplicito, invece di essere ignorata
dall'API e restituire l'intero catalogo:

```bash
openrndt search --bbox "11.2,44.4,11.5"
# `bbox` richiede quattro valori xmin,ymin,xmax,ymax (ricevuti 3: '11.2,44.4,11.5').
```

Il timeout HTTP per singolo tentativo è configurabile con `--timeout` (default 30s);
con i retry su timeout/5xx (3 tentativi) il caso peggiore è ~3x questo valore:

```bash
openrndt --timeout 5 search --q "catasto" --num 5
```

Per sapere quale versione è installata:

```bash
openrndt --version
```

Tutti i comandi accettano `--format json` (default), `--format table`, `--format csv`.
Unica eccezione al default: `search --profile ...` senza `--format` esplicito esce
in `table`, dato che i preset di colonne valgono solo per gli output tabellari.
Per `search` c'è anche `--format compact`: una riga NDJSON per record con i soli
campi ad alto segnale (`id`, `title`, `org`, `type`, `category`, `updated`,
`indexed`, `open`, `license`, `url`, `geolibre_url`, `resources`, `email`, `download`), pensata
per agenti AI e pipe a basso consumo di token:

```bash
openrndt --format compact search --q "stato chimico dei fiumi" --num 3
```

Ecco una riga reale (uno dei tre record):

```
{"id": "arpa_ve:StatoChimicoFiumi_DGR1856", "title": "Stato chimico fiumi 2010-2013 (DGR 1856/2015)", "org": "ARPAV - U.O. Transizione Digitale e ICT", "type": "dataset", "category": "inlandWaters", "updated": "2017-12-20T00:00:00Z", "indexed": "2026-04-25T15:55:59.587Z", "open": false, "license": null, "url": "https://geodati.gov.it/geoportal-catalog/rest/metadata/item/arpa_ve%3AStatoChimicoFiumi_DGR1856/html", "resources": ["WFS", "WMS"]}
```

`email` è l'indirizzo del punto di contatto designato della scheda e `download`
la lista degli URL di download dichiarati (`url_download_s` e
`url_http_download_s`, riportati come sono: il RNDT ci mette anche endpoint che
download diretti non sono). Insieme rispondono alle due domande che vengono
subito dopo una ricerca: chi contatto, e da dove scarico.

`open`, `license` e `url` servono a chi deve riusare o citare il dato. `open`
riporta quello che l'ente ha dichiarato nel campo `isOpendata`, la definizione di
dato aperto di RNDT: `open: false` significa che l'ente non l'ha dichiarato lì,
non che il dato sia chiuso (misurato su 3000 record: il campo è presente sul 72%,
che scende al 55% escludendo l'Agenzia delle Entrate, e in un terzo dei casi
contiene il solo marcatore `opendata`). `license` prende la licenza da
`isOpendata` e, se lì non c'è, dai vincoli d'uso (`apiso_OtherConstraints_s`,
`apiso_AccessConstraints_s`), dove molte schede la dichiarano nel blocco INSPIRE:
le ortofoto AGEA e il DUSAF lombardo hanno `open: false` e `license` CC BY 4.0.
Il valore non è normalizzato: può essere `CC BY 4.0`, un URL o un intero
paragrafo di disclaimer. `url` è il permalink della scheda sul portale, da
mettere in nota quando si cita la fonte. In `--format table` `url` non viene
stampata, `open` esce come sì/no e `license` è troncata: in `csv` e `compact`
restano intere.

`geolibre_url` apre lo stesso record in [GeoLibre](https://geolibre.app) web, dentro il plugin [openrndt-geolibre](https://github.com/ondata/openrndt-geolibre): `https://web.geolibre.app/?plugin=openrndt-geolibre&rndt=<id>`. Il pannello si apre sulla scheda, con i servizi WMS/WFS pronti da aggiungere alla mappa; a chi non ha il plugin GeoLibre lo propone con «Trust and load». C'è in tutti gli output tranne `--format table`, anche nel JSON di `search` accanto a ogni risultato. Funziona su web.geolibre.app, non ancora in GeoLibre Desktop (la 3.2.0 non legge `?plugin=` per i plugin del registro) né con `layout=viewer` ([opengeos/GeoLibre#2898](https://github.com/opengeos/GeoLibre/issues/2898)).

`get` dà anche `geolibre_map_url`, subito dopo `geolibre_url`: lo stesso record con il suo layer già sulla mappa, quando ce n'è uno che GeoLibre web sa disegnare. Per trovarlo `get` legge le capabilities dei WMS e WMTS della scheda (come `resources --layers`) e sceglie il layer come il plugin: quello nominato da un link della scheda (`LAYERS=`), altrimenti l'unico, altrimenti quello col titolo più vicino a quello della scheda. Valgono i WMTS in griglia Web Mercator le cui tile rispondono con CORS e i WMS https con CORS offerti in EPSG:3857; altrimenti il campo è `null`. Un WMS che dichiara solo un sistema nazionale vale se il server lo disegna lo stesso in EPSG:3857: lo dice una GetMap di prova, come nel plugin (ortofoto 2015 della Lombardia, solo EPSG:32632 dichiarato). `--no-map-link` salta queste chiamate di rete. I link WMTS richiedono il plugin 0.5.0, nel registro dal 2026-11-01. `get` e `search --id` accettano anche il fileid di una scheda quando è diverso dal suo id nel catalogo (le ortofoto AGEA: `agea:OI:ORTOIMMAGINI:m004` è `agea:OI:DATEVOLO:m001+-++-+2026-09-25+12:42:55`).

`--geolibre-link` dà invece l'indirizzo che apre l'intera ricerca nel plugin, con i footprint sulla mappa (plugin 0.3.8 o successivo):

```bash
openrndt search --q fiumi --bbox 9,45,10,46 --published-from 2020-01-01 --geolibre-link
# https://web.geolibre.app/?plugin=openrndt-geolibre&rndt=fiumi&rndtBbox=9,45,10,46&rndtDate=publication&rndtFrom=2020-01-01
```

I filtri che il plugin non ha (`--time`, `--modified`, alcuni `--sort`) il link li ignora e la CLI li elenca su stderr. Con `--format json` lo stesso link è nell'oggetto `geolibre_search`, accanto a `total`. Il link riapre la ricerca dal vivo, sulla prima pagina.

`updated` è la data della **scheda di metadato** (`apiso_Modified_dt`), la stessa
su cui filtrano `--updated-from/--updated-to`; `indexed` è l'istante in cui il
catalogo ha indicizzato il record (`sys_modified_dt`) e non dice nulla né sul dato
né sulla scheda. Attenzione se leggi il JSON grezzo dell'API (`--format json`):
lì il campo top-level `updated` è quello di indicizzazione, mentre la data della
scheda sta in `_source.apiso_Modified_dt`.

### Ricerca per ente

Per un ente la via consigliata è il **codice IPA**: prima lo trovi dal nome, poi filtri con `--ipa`.

```bash
openrndt discover --what ipa --match torino   # c_l219 Comune di Torino (269 schede), cmto Città metropolitana (247)
openrndt search --ipa c_l219 --num 5          # 269 record
openrndt search --ipa r_sardeg                # 766 record, anche quelli con il prefisso R_SARDEG
```

`--ipa` filtra sul codice IPA dell'ente titolare, che nel RNDT è il prefisso dell'id di ogni scheda. Non dipende da come è scritto il nome: la Città metropolitana di Torino ha due grafie, ARPA Veneto tre (per esteso, «ARPAV» e «…Protezione dell'Ambiente del Veneto»), e `--ipa cmto` e `--ipa arpa_ve` (245) le trovano tutte. Trova anche le schede senza ente responsabile (192 nel catalogo). Il prefisso nel catalogo non ha maiuscole uniformi (`PCM`, `R_SARDEG` e `r_sardeg`), e la CLI lo cerca senza distinguerle. Più codici si separano con la virgola.

`discover --what ipa` è un vocabolario offline dei codici presenti nel RNDT (179), con nome, acronimo e categoria dell'Indice PA (`L6`, «Comuni e loro Consorzi e Associazioni»); `--match` cerca nel codice, nel nome, nell'acronimo e nei nomi usati nelle schede (`--match arpae` → `arpa`). Se nel vocabolario non c'è nulla, cerca nell'anagrafica completa dell'Indice PA (23.757 enti, anche questa nel pacchetto) e restituisce gli enti con `schede: 0`: `--match "comune di palermo"` → `c_g273`, perché il Comune di Palermo è nell'Indice PA ma non pubblica sul RNDT. Il nome è giusto, quindi i dati vanno cercati presso un ente sovraordinato o per territorio. Lo stesso ente lo segnala `--org` su zero risultati.

Due limiti: `--ipa arpa_ve` non trova 11 schede ARPAV il cui id non ha il codice, e in pochi casi l'ente responsabile non è il titolare IPA (`m_d`, Ministero della Difesa, ha schede dell'Istituto Geografico Militare).

`--org` è la seconda strada: cerca l'ente responsabile (`EnteResponsabile_s`) che contiene il testo, senza distinzione di maiuscole, come il plugin openrndt-geolibre. Le sigle non bastano, perché l'ente è scritto per esteso.

```bash
openrndt search --org "comune di torino" --num 5      # 269 record, solo Comune di Torino
openrndt search --org "regione piemonte" --num 5      # 613 record, anche «Regione Piemonte - A1601B - …»
openrndt search --org-exact "Comune di Torino"        # confronto esatto su EnteResponsabile_s
```

Evita le wildcard su `contact_organizations_s`: sono case-sensitive
(`*bologna*` → 0, `*Bologna*` → 112) e pescano ogni record che *nomina* quel
territorio, anche di altri enti.

Se `--org` non trova nulla, la CLI interroga il catalogo e ti mostra i nomi di ente realmente presenti che somigliano a quello cercato, e i codici IPA del vocabolario che contengono il testo: utile perché molti comuni non pubblicano in proprio e i loro dati stanno sotto un ente sovraordinato.

```
$ openrndt search --org "comune di bologna"
Nessun risultato per la ricerca.
Suggerimenti: enti simili presenti in catalogo: Citta' Metropolitana di Bologna | Agenzia Regionale per La Sicurezza Territoriale e La Protezione Civile | Regione Emilia-Romagna
```

Per `--org arpae` il suggerimento è `--ipa arpa` (383 schede).

Se `resources` è `[]` il record non linka servizi fruibili: recupera il
dettaglio con `get <id>` e guarda `_source.links_s` (spesso il download è
dietro un portale dell'ente, non un link diretto).

## Esempi verificati

Tutti gli esempi qui sotto sono stati **eseguiti live contro il catalogo reale** il
2026-08-09: i comandi riportano output veri, gli URL rispondono 200, i layer
esistono. I totali cambiano perché il catalogo cresce — sono il conteggio di quel
giorno, non una promessa.

### 1. Dal tema al GeoPackage: dati vettoriali scaricati in ~5 secondi

> Il caso più comune per un tecnico GIS: serve il dato, non il metadato.

```bash
# 1. trova il record con un servizio WFS (la colonna resources lo dice subito)
openrndt --format compact search --q "stato chimico dei fiumi" --num 3
# → arpa_ve:Stato_Chimico_Fiumi_DGR_3_2022 … resources: ["WFS", "WMS"]

# 2. estrai gli endpoint del record
openrndt --format json resources arpa_ve:Stato_Chimico_Fiumi_DGR_3_2022 --no-check
# WFS  http://gaia.arpa.veneto.it/geoserver/ows?service=WFS&version=1.0.0&request=GetCapabilities
# WMS  http://gaia.arpa.veneto.it/geoserver/ows?service=wms&version=1.3.0&request=GetCapabilities

# 3. scarica il layer vettoriale in GeoPackage (open source, apribile in QGIS)
ogr2ogr -f GPKG stato_fiumi.gpkg \
  "WFS:https://gaia.arpa.veneto.it/geoserver/ows?service=WFS&version=1.0.0&request=GetCapabilities" \
  geonode:Stato_Chimico_Fiumi_DGR_3_2022 -nlt PROMOTE_TO_MULTI
# → stato_fiumi.gpkg (585 KB) pronto per QGIS, in ~2 secondi
```

Nota onesta: la scheda cataloga l'endpoint in `http`, il servizio risponde con un
redirect a `https` che `ogr2ogr` segue da solo (per questo `resources` senza
`--no-check` segnala `301`, non `200`).

### 2. L'uso del suolo in QGIS: un WMS con 7 annate (più il 1853)

> Un solo URL da incollare in QGIS per avere l'uso del suolo dell'Emilia-Romagna
> dal 1976 a oggi, e in più l'uso storico del 1853.

```bash
openrndt search --q "uso del suolo WMS" --num 20
```

Il record `r_emiro:2016-04-01T154419` ("Uso del Suolo (WMS)") pubblica:

```
http://servizigis.regione.emilia-romagna.it/wms/uso_del_suolo?request=GetCapabilities&service=WMS
```

In QGIS: *Aggiungi layer WMS/WMTS* → questo URL. I layer coprono le annate
2020, 2017, 2014, 2008, 2003, 1994, 1976 più l'uso storico 1853 (punti e
poligoni) — confermato dal GetCapabilities del servizio.

### 3. Il catasto urbano come layer: WMS del Comune di Torino

```bash
openrndt search --q "catasto" --num 10
```

Tra i risultati c'è il *Catasto Urbano 1:1500 - Geo-servizio WMS* con URL
verificato (HTTP 200):

```
https://geomap.reteunitaria.piemonte.it/ws/siccms/coto-01/wmsg01/wms_sicc17bis_catasto_urbano?service=WMS&version=1.1.1&request=getCapabilities
```

### 4. Le ortofoto più fresche d'Italia: la 2024 di Regione Lombardia

```bash
openrndt --format csv search --q "ortofoto" --profile qgis --num 100
```

Il profilo `qgis` produce un CSV con la colonna `wms_url` già pronta: qui sotto
tre servizi verificati (HTTP 200) da incollare in QGIS:

| Ente | Dato | URL WMS |
|---|---|---|
| Regione Lombardia | Ortofoto 2024 | `https://www.cartografia.servizirl.it/arcgis5/services/BaseMap/Ortofoto2024/ImageServer/WMSServer?request=GetCapabilities&service=WMS` |
| Regione Sardegna | Ortofoto | `https://webgis.regione.sardegna.it/geoserverraster/ows?service=wms&version=1.3.0&request=GetCapabilities` |
| Regione Piemonte | Ortofoto (mapproxy) | `https://geomap.reteunitaria.piemonte.it/mapproxy/service?service=WMS&version=1.3.0&request=getCapabilities` |

### 5. Il reticolo idrografico in vettoriale (non un'immagine)

> Per interrogare e modificare i dati serve un WFS, non un WMS.

```bash
openrndt --format compact search --q "reticolo idrografico" --num 50
```

Due servizi verificati (HTTP 200, risposta in ~3s):

- **ARPA Veneto** — `http://gaia.arpa.veneto.it/geoserver/ows?service=WFS&version=1.0.0&request=GetCapabilities`
- **ISPRA** — `http://sdi.isprambiente.it/geoserver/hy/wfs?service=wfs&version=2.0.0&request=GetCapabilities`

In QGIS: *Aggiungi layer WFS* → URL → scegli il feature type. Da CLI, lo stesso
flusso dell'esempio 1 (`ogr2ogr`) scarica il layer in GeoPackage.

### 6. Tutti i WMS di un tema INSPIRE in 10 secondi

> Quanti servizi WMS pubblicano gli enti italiani su un tema? Un one-liner.

```bash
openrndt --format json search --q 'INSPIRETheme_s:Idrografia' --num 862 \
  | jq -r '.results[].links[]? | select(.dctype=="WMS") | .href' | sort -u > wms_idrografia.txt
wc -l wms_idrografia.txt
# 108 endpoint WMS unici, estratti in ~10 secondi
```

### 7. Cosa copre la mia area di studio

> Bounding box + parola chiave: dalla cartografia odierna al Ducato di Modena 1821.

```bash
openrndt --format json search --q "edificato" --bbox "11.2,44.4,11.5,44.6" --num 10
# total: 44 (2026-08-09)
```

Nel riquadro bolognese ci sono il Database Topografico Regionale (edifici,
unità volumetriche, falde) **e** cartografie storiche esposte come WMS,
per esempio:

```
Carta storica del Ducato di Modena - 1821 (WMS)
→ https://servizigis.regione.emilia-romagna.it/wms/Ducato_modena_1821?request=GetCapabilities&service=WMS   (HTTP 200)
```

Nota: il filtro bbox è per *sovrapposizione*: include i dataset a copertura
regionale che toccano l'area (per questo il totale è 44, non "quelli di Bologna").

### 8. I dati del mio comune: 4 dataset, con il contatto per il riuso

> Il caso dell'ufficio comunale: cosa pubblica chi gestisce il mio territorio,
> e a chi scrivere per il riuso.

```bash
openrndt --format compact search \
  --q "(Bologna OR bolognese) AND AmbitoTerritoriale_s:Locale" \
  --bbox 11.2,44.4,11.5,44.6 --num 10
# total: 4 — tutti della Città metropolitana di Bologna:
#   Infrastrutture CMBO · Fermate SFM CMBO · Tracciato linee ferroviarie CMBO · Tracciato strade provinciali CMBO
```

Il dettaglio di un record dà anche il punto di contatto per chiedere aggiornamenti
o il riuso:

```bash
openrndt get <id> | jq -r '._source | "\(.EnteResponsabile_s) | \(.PuntoDiContattoEmail_s)"'
# Citta' metropolitana di Bologna | segreteria.pianificazione@cittametropolitana.bo.it
```

Trucco che fa la differenza: col solo bbox si prendono 2.789 record (molti
dichiarano una bbox nazionale, rumore); aggiungendo `AmbitoTerritoriale_s:Locale`
e una parola chiave del territorio si arriva a 4 record precisi.

Qui la ricerca è per territorio e non per ente perché il Comune di Bologna non
pubblica in proprio: `openrndt search --org "comune di bologna"` dà 0 e ti indica
chi pubblica davvero (`Citta' metropolitana di Bologna`, `Regione
Emilia-Romagna`). Dove l'ente c'è, il codice IPA è la via diretta: `openrndt search
--ipa c_l219` (Comune di Torino) → 269 record.

### 9. Solo open data: 268 dataset sulle frane, con licenza

```bash
openrndt --format compact search --q "frane AND isOpendata:*" --num 10
# total: 268 (2026-08-09) — inventari IFFI, rilievi post-alluvione 2023, pericolosità…
```

Per una licenza specifica si filtra sul valore: `--q 'frane AND isOpendata:"CC BY 4.0"'`.
Il dettaglio del record riporta la licenza esatta in `isOpendata` e
`apiso_AccessConstraints_s`.

### 10. Dati, licenza e citazione della fonte per un articolo

> ISPRA pubblica "Popolazione a rischio alluvioni" con licenza CC-BY-4.0:
> riutilizzabile citando la fonte.

```bash
openrndt get ispra_rm:01IdroHazard_DT | jq \
  '{licenza: ._source.isOpendata, ente: ._source.EnteResponsabile_s, email: ._source.PuntoDiContattoEmail_s}'
# licenza: "Dato concesso con licenza CC-BY-4.0"
# ente:    Istituto Superiore per la Protezione e la Ricerca Ambientale
# email:   sinaservice@isprambiente.it
```

Citazione d'esempio: *"Fonte: ISPRA — Popolazione a rischio alluvioni, CC-BY 4.0"*.
I dati sono esposti come WFS su `sdi.isprambiente.it` e si scaricano con
`ogr2ogr` come nell'esempio 1.

### 11. Il catalogo sulla mappa: footprint in GeoJSON

> Vedi a colpo d'occhio quali dataset coprono la tua area, direttamente in QGIS.

```bash
openrndt footprints --q "frane AND isOpendata:*" --num 268 > frane_footprints.geojson
```

`footprints` esporta una `FeatureCollection` EPSG:4326 con le bbox dei record
(id, title, org, type, resources): trascina il file in QGIS e ogni poligono è
un dataset, con i dati essenziali negli attributi.

## Uso come libreria Python

```python
from openrndt import search, get_item, item_record, get_item_xml, ItemNotFoundError

# Ricerca
results = search(q="catasto", num=5)
for r in results["results"]:
    print(r["id"], r["title"])

# Filtro per categoria e bbox
results = search(data_category="planningCadastre", bbox="7,44,8,45", num=10)

# Filtro per tema o cluster INSPIRE; inspire_tree() dà l'elenco offline
results = search(inspire_theme="hy", ipa="r_toscan", num=10)

# Dettaglio singolo metadato: get_item dà la busta Elasticsearch grezza,
# item_record il documento normalizzato (lo stesso che stampa la CLI)
item = get_item("age:D_E973_MARSAGLIA")
record = item_record(item)
print(record["title"], record["data_date"], record["contact"]["email"])
for r in record["resources"]:
    print(r["type"], r["url"])

# XML ISO 19139
xml = get_item_xml("age:D_E973_MARSAGLIA")

# Gestione ID inesistente
try:
    item = get_item("id_inesistente")
except ItemNotFoundError:
    print("metadato non trovato")
```

Sono esposti anche i mattoni del documento: `contact_point`, `download_urls` e
`bbox_from_envelope` lavorano direttamente su un `_source`, e `compact_results`,
`record_dates`, `record_license`, `record_url`, `organization_names` sulle
risposte di `search`.

Le funzioni propagano le eccezioni `httpx`: `httpx.HTTPStatusError` per le
risposte 4xx/5xx e `httpx.ConnectError` / `httpx.TimeoutException` per i
problemi di rete. I retry interni coprono i timeout e i 5xx (3 tentativi),
mentre gli errori di connessione/DNS (`ConnectError`) vengono propagati subito.
Tutte derivano da `httpx.HTTPError`, comodo per catturarle insieme:

```python
import httpx
from openrndt import search

try:
    results = search(q="catasto")
except httpx.HTTPError as exc:
    print(f"richiesta fallita: {exc}")
```

Il base URL è configurabile via variabile d'ambiente o parametro:

```python
from openrndt.config import set_base_url
set_base_url("https://mio-mirror.example.com/RNDT")
```

## Per agenti AI

L'utente primario di questa CLI è un agente che legge `stdout` e compone i comandi
passo passo. Da qui i principi di design (sul modello di
[opensdmx](https://github.com/ondata/opensdmx)):

- **Output strutturato, mai oggetti Python.** Default JSON su `stdout`; `--format
  table` per la lettura umana, `--format csv` per i risultati tabellari, `--format
  compact` (NDJSON, una riga per record) per scremare molti risultati a basso costo.
- **In modalità JSON, `stdout` contiene solo JSON.** Errori e avvisi vanno su
  `stderr`: si può fare pipe diretta in `jq`.
- **Errori leggibili e self-contained: mai stack trace.** Un errore di rete o HTTP
  produce un messaggio comprensibile su `stderr` ed exit code `1`, non un traceback.
- **Exit code chiari.** `0` successo, `1` errore (rete, HTTP, ID inesistente),
  `2` parametri non validi.
- **Niente formati ambigui.** `get <id> --format csv` (dettaglio non tabellare)
  fallisce con un messaggio esplicito invece di restituire output vuoto.

### La skill `rndt-explorer` — esplorazione guidata

Il repo include una **Agent Skill** per Claude Code:
[`skills/rndt-explorer/`](https://github.com/ondata/openrndt/blob/main/skills/rndt-explorer/SKILL.md). Guida l'agente
attraverso 4 fasi: scoperta delle codelist (offline), ricerca con filtri
progressivi, lettura del dettaglio, individuazione delle risorse scaricabili
(WMS, WFS, download diretto). Include workflow pronti e verificati per casi
d'uso reali — dall'operatore GIS che vuole un layer per QGIS al data journalist
che deve scaricare i dati, verificarne la licenza e citare la fonte.

**Installazione** (dopo aver installato la CLI):

```bash
git clone https://github.com/ondata/openrndt.git
mkdir -p ~/.claude/skills
cp -r openrndt/skills/rndt-explorer ~/.claude/skills/
```

Da quel momento Claude Code attiva la skill da solo quando chiedi dati
territoriali italiani — «mi serve il catasto della mia zona», «trova un WMS
con le ortofoto della Sardegna» — senza che tu debba nominarla.

### Vedere i dati su una mappa: GeoLibre (consigliato)

La skill ha una fase opzionale di visualizzazione che usa
[GeoLibre](https://geolibre.app): porta su una mappa i risultati della ricerca,
un servizio WMS/WFS o un file scaricabile. Non serve per usare la CLI, ma per
questa fase ne consigliamo l'installazione:

- **l'app**, da <https://geolibre.app/downloads/>, con le istruzioni per ogni
  sistema operativo;
- **il server MCP**, con cui l'agente costruisce i progetti di mappa:

```bash
uv tool install "geolibre[mcp]"
claude mcp add geolibre -- geolibre-mcp --root ~/maps
```

## Il plugin per GeoLibre: openrndt-geolibre

[openrndt-geolibre](https://github.com/ondata/openrndt-geolibre) è un plugin di [GeoLibre](https://geolibre.app) che porta la ricerca nel RNDT dentro la mappa. È la controparte grafica di questa CLI e usa la stessa API REST del catalogo.

Dal pannello si cerca per testo, tipo di risorsa, area (la vista della mappa, un riquadro o le forme disegnate), servizi disponibili (WMS, WFS, ArcGIS REST), tema INSPIRE, ente e date. I risultati compaiono come footprint sulla mappa; la scheda di un record elenca i suoi layer WMS e WFS, che si aggiungono alla mappa con un clic. Una ricerca o un record si condividono come link, e **Copy for an agent** copia la ricerca in Markdown, con il comando `curl` e il modo di proseguire con `openrndt`.

Per provarlo:

- **GeoLibre web**: <https://web.geolibre.app/?plugin=openrndt-geolibre>. Chi non ha il plugin lo installa dopo la richiesta «Trust and load».
- **GeoLibre Desktop** (dalla 3.2.0): **Settings > Manage Plugins**, poi **RNDT catalogue** e **Install**.

Il collegamento con la CLI sono i link a GeoLibre web: `geolibre_url` per ogni record in uscita da `search`, `get` e `footprints`, un link per layer da `resources --layers`, e `search --geolibre-link` per l'intera ricerca (vedi sopra, nella sezione sui campi). Il plugin è in beta; problemi e idee vanno nelle [issue del suo repository](https://github.com/ondata/openrndt-geolibre/issues).

## Riferimenti

- Pagina ufficiale REST API: <https://geodati.gov.it/geoportale/eng/strumenti-en/rest-api>
- Spec completa (sito di test Esri Geoportal Server, non produzione): <https://gpt.geocloud.com/geoportal3/api/gpt_api.json>
- Documentazione raccolta nella cartella [`ref/`](https://github.com/ondata/openrndt/tree/main/ref).

## Licenza

MIT.