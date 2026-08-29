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

> Stato: v2.0 — read-only.

## Cos'è il RNDT

Il [Repertorio Nazionale dei Dati Territoriali](https://geodati.gov.it/geoportale/) è
il catalogo ufficiale italiano dei metadati geografici (ISO 19115/19139). Espone REST
API per cercare e scaricare i metadati.

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

# Filtro per bounding box (Piemonte sud)
openrndt search --q "cartografia" --bbox 7,44,8,45 --num 10

# Profilo GIS (campi essenziali). Senza --format l'output diventa una tabella
openrndt search --q "catasto" --profile gis --num 10

# Profilo QGIS (CSV con colonne URL servizi + bbox separata)
openrndt --format csv search --q "catasto" --profile qgis --num 10

# Cosa pubblica un ente (campo analizzato: case-insensitive)
openrndt search --org "comune di torino" --num 10

# Filtri temporali avanzati (aggiornamento + pubblicazione)
openrndt search --q "catasto" --updated-from 2024-01-01 --published-from 2020-01-01 --num 10

# Export footprint bbox in GeoJSON (EPSG:4326)
openrndt footprints --q "catasto" --num 50 > footprints.geojson

# Per categoria tematica ISO 19115
openrndt search --data-category planningCadastre --num 5

# Singolo metadato
openrndt get age:D_E973_MARSAGLIA

# Estrai e verifica endpoint WMS/WFS/download di un metadato
openrndt resources age:D_E973_MARSAGLIA

# XML ISO 19139 grezzo
openrndt get age:D_E973_MARSAGLIA --xml > meta.xml

# Codelist disponibili (no rete)
openrndt discover
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
`indexed`, `open`, `license`, `url`, `resources`), pensata per agenti AI e pipe a
basso consumo di token:

```bash
openrndt --format compact search --q "stato chimico dei fiumi" --num 3
```

Ecco una riga reale (uno dei tre record):

```
{"id": "arpa_ve:StatoChimicoFiumi_DGR1856", "title": "Stato chimico fiumi 2010-2013 (DGR 1856/2015)", "org": "ARPAV - U.O. Transizione Digitale e ICT", "type": "dataset", "category": "inlandWaters", "updated": "2017-12-20T00:00:00Z", "indexed": "2026-04-25T15:55:59.587Z", "open": false, "license": null, "url": "https://geodati.gov.it/geoportal-catalog/rest/metadata/item/arpa_ve%3AStatoChimicoFiumi_DGR1856/html", "resources": ["WFS", "WMS"]}
```

`open`, `license` e `url` servono a chi deve riusare o citare il dato. `open` e
`license` riportano quello che l'ente ha dichiarato nel campo `isOpendata`, senza
normalizzarlo: `license` può essere `CC BY 4.0` come un intero paragrafo di
disclaimer, e `open: false` significa che l'ente non l'ha dichiarato lì, non che
il dato sia chiuso (misurato su 3000 record: il campo è presente sul 72%, che
scende al 55% escludendo l'Agenzia delle Entrate, e in un terzo dei casi contiene
il solo marcatore `opendata`). `url` è il permalink della scheda sul portale, da
mettere in nota quando si cita la fonte. In `--format table` `url` non viene
stampata, `open` esce come sì/no e `license` è troncata: in `csv` e `compact`
restano intere.

`updated` è la data della **scheda di metadato** (`apiso_Modified_dt`), la stessa
su cui filtrano `--updated-from/--updated-to`; `indexed` è l'istante in cui il
catalogo ha indicizzato il record (`sys_modified_dt`) e non dice nulla né sul dato
né sulla scheda. Attenzione se leggi il JSON grezzo dell'API (`--format json`):
lì il campo top-level `updated` è quello di indicizzazione, mentre la data della
scheda sta in `_source.apiso_Modified_dt`.

### Ricerca per ente

`--org` cerca la frase su `apiso_OrganizationName_txt`, campo analizzato: non
conta il maiuscolo, né l'ordine dei token, né gli apostrofi.

```bash
openrndt search --org "comune di torino" --num 5      # 269 record, solo Comune di Torino
openrndt search --org-exact "Comune di Torino"        # confronto esatto su EnteResponsabile_s
```

Evita le wildcard su `contact_organizations_s`: sono case-sensitive
(`*bologna*` → 0, `*Bologna*` → 112) e pescano ogni record che *nomina* quel
territorio, anche di altri enti.

Se `--org` non trova nulla, la CLI interroga il catalogo e ti mostra i nomi di
ente realmente presenti che somigliano a quello cercato — utile perché molti
comuni non pubblicano in proprio e i loro dati stanno sotto un ente
sovraordinato:

```
$ openrndt search --org "comune di bologna"
Nessun risultato per la ricerca.
Suggerimenti: enti simili presenti in catalogo: Citta' metropolitana di Bologna | Regione Emilia-Romagna
```

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
Emilia-Romagna`). Dove l'ente c'è, `--org` è la via diretta: `openrndt search
--org "comune di torino"` → 269 record.

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
from openrndt import search, get_item, get_item_xml, ItemNotFoundError

# Ricerca
results = search(q="catasto", num=5)
for r in results["results"]:
    print(r["id"], r["title"])

# Filtro per categoria e bbox
results = search(data_category="planningCadastre", bbox="7,44,8,45", num=10)

# Dettaglio singolo metadato
item = get_item("age:D_E973_MARSAGLIA")
print(item["_source"]["title"])

# XML ISO 19139
xml = get_item_xml("age:D_E973_MARSAGLIA")

# Gestione ID inesistente
try:
    item = get_item("id_inesistente")
except ItemNotFoundError:
    print("metadato non trovato")
```

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

## Riferimenti

- Pagina ufficiale REST API: <https://geodati.gov.it/geoportale/eng/strumenti-en/rest-api>
- Spec completa (sito di test Esri Geoportal Server, non produzione): <https://gpt.geocloud.com/geoportal3/api/gpt_api.json>
- Documentazione raccolta nella cartella [`ref/`](https://github.com/ondata/openrndt/tree/main/ref).

## Licenza

MIT.