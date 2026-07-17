# openrndt

CLI Python e libreria per accedere al **Repertorio Nazionale dei Dati Territoriali (RNDT)** —
pensata per essere orchestrata da un'AI.

> Stato: v1.0 — read-only.

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

> Non ancora pubblicato su PyPI (roadmap verso la v1.0). Nel frattempo installa da locale.

### Da locale

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

# Per categoria tematica ISO 19115
openrndt search --data-category planningCadastre --num 5

# Singolo metadato
openrndt get age:D_E973_MARSAGLIA

# XML ISO 19139 grezzo
openrndt get age:D_E973_MARSAGLIA --xml > meta.xml

# Codelist disponibili (no rete)
openrndt discover
```

Il timeout HTTP per singolo tentativo è configurabile con `--timeout` (default 30s);
con i retry su timeout/5xx (3 tentativi) il caso peggiore è ~3x questo valore:

```bash
openrndt --timeout 5 search --q "catasto" --num 5
```

Tutti i comandi accettano `--format json` (default), `--format table`, `--format csv`.
Per `search` c'è anche `--format compact`: una riga NDJSON per record con i soli
campi ad alto segnale (`id`, `title`, `org`, `type`, `category`, `updated`,
`resources`), pensata per agenti AI e pipe a basso consumo di token.

```bash
openrndt --format compact search --q "catasto" --num 3
# {"id":"…","title":"…","org":"Comune di Torino","type":"service","category":null,"updated":"…","resources":["WMS"]}
```

## Esempi di conversazione con un'AI

openrndt è pensato per essere **pilotato da un assistente AI**. Non devi imparare la
sintassi: descrivi a parole quello che ti serve e l'AI compone i comandi, legge i
risultati e ti restituisce ciò che conta — di solito **un URL WMS/WFS da incollare in
QGIS** o un dato da scaricare. Tutti gli esempi qui sotto usano risposte reali del
catalogo RNDT.

> Per provarli serve un assistente (es. Claude) a cui è stata installata la skill
> `skills/rndt-explorer/` o che può eseguire `openrndt` da terminale.

### «Mi serve l'uso del suolo dell'Emilia-Romagna da caricare in QGIS»

> **Tu:** Sto lavorando su un progetto QGIS in Emilia-Romagna. Mi trovi un servizio
> con l'uso del suolo regionale, così lo aggiungo come layer?

L'AI cerca i servizi pubblicati sul tema:

```bash
openrndt search --q "uso del suolo WMS" --num 20
```

> **AI:** Trovato. La **Regione Emilia-Romagna** pubblica un WMS *Uso del Suolo* che
> copre più annate (2020, 2017, 2014, 2008, 2003, 1994, 1976) più l'uso storico dal
> 1853. In QGIS aggiungi un nuovo layer **WMS/WMTS** con questo URL:
>
> ```
> http://servizigis.regione.emilia-romagna.it/wms/uso_del_suolo?request=GetCapabilities&service=WMS
> ```
>
> Scegli poi l'annata che ti interessa fra i layer offerti dal servizio.

### «Voglio il catasto di un comune piemontese»

> **Tu:** Mi serve il catasto urbano per un'analisi in Piemonte.

```bash
openrndt search --q "catasto" --num 10
```

> **AI:** C'è il **Catasto Urbano 1:1500** come geo-servizio WMS della Regione
> Piemonte. URL per QGIS:
>
> ```
> https://geomap.reteunitaria.piemonte.it/ws/siccms/coto-01/wmsg01/wms_sicc17bis_catasto_urbano?service=WMS&version=1.1.1&request=getCapabilities
> ```

### «Cerco ortofoto da usare come base»

> **Tu:** Mi servono delle ortofoto come sfondo per la mia mappa. Cosa c'è disponibile?

```bash
openrndt search --q "ortofoto" --num 50
```

> **AI:** Diverse amministrazioni espongono ortofoto via WMS, pronte da usare come
> base in QGIS. Per esempio:
>
> - **Regione Sardegna** — `https://webgis.regione.sardegna.it/geoserverraster/ows?service=wms&version=1.3.0&request=GetCapabilities`
> - **Provincia di Lodi** — `http://sdi.provincia.lodi.it/arcgis/services/DBTL/dbtl_ortofoto_digitali/MapServer/WMSServer?request=GetCapabilities&service=WMS`
> - **Regione Piemonte** — `https://geomap.reteunitaria.piemonte.it/mapproxy/service?service=WMS&version=1.3.0&request=getCapabilities`

### «Il reticolo idrografico, ma vettoriale (per editing)»

> **Tu:** Non voglio un'immagine: mi serve il reticolo idrografico come vettoriale,
> così posso interrogarlo e modificarlo.

```bash
openrndt search --q "reticolo idrografico" --num 50
```

> **AI:** Per i vettoriali ti serve un **WFS** (in QGIS: *Aggiungi layer WFS*). Alcuni
> servizi disponibili:
>
> - **ISPRA** — `http://sdi.isprambiente.it/geoserver/hy/wfs?service=wfs&version=2.0.0&request=GetCapabilities`
> - **ARPA Veneto** — `http://gaia.arpa.veneto.it/geoserver/ows?service=WFS&version=1.0.0&request=GetCapabilities`
> - **Regione Basilicata** — `http://rsdi.regione.basilicata.it/rbgeoserver2016/dbgt_0404/nd_idr/wfs?request=GetCapabilities&service=WFS&version=2.0.0`

### «Tutto quello che pubblica un certo ente»

> **Tu:** Quanti e quali dataset ha pubblicato la Regione Lombardia?

```bash
openrndt search --q 'apiso_OrganizationName_txt:"Regione Lombardia"' \
  --sort "apiso_Modified_dt:desc" --num 10
```

> **AI:** La **Regione Lombardia** ha **430 dataset** nel RNDT. Ecco i 10 aggiornati
> più di recente… (l'AI elenca titoli e date). Posso filtrarli per tema — uso del
> suolo, idrografia, trasporti — o mostrarti solo quelli con un servizio WMS/WFS.

### «Cosa copre la mia area di studio»

> **Tu:** Sto studiando l'area attorno a Bologna. Quali dataset la coprono?

```bash
openrndt search --q "edificato" --bbox "11.2,44.4,11.5,44.6" --num 10
```

> **AI:** Nel riquadro che copre l'area bolognese ci sono **40 dataset** che la
> intersecano: il Database Topografico Regionale (edifici, unità volumetriche, falde)
> e anche cartografie storiche (Ducato di Modena 1821, territorio ferrarese 1814)
> disponibili come WMS. Nota: il filtro è per *sovrapposizione* al riquadro, quindi
> include dataset a copertura regionale che toccano l'area.

### «Solo dati con licenza aperta»

> **Tu:** Mi servono dati sulle frane, ma solo open data che posso riusare liberamente.

```bash
openrndt search --q "frane AND isOpendata:*" --num 10
```

> **AI:** Ci sono **259 dataset open data** sulle frane — dall'inventario IFFI della
> Regione Toscana ai rilievi con drone dell'emergenza alluvione 2023 in
> Emilia-Romagna. Te li elenco con la licenza di ciascuno?

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
[opensdmx](https://github.com/aborruso/opensdmx)):

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

Il progetto include inoltre una skill Claude Code in `skills/rndt-explorer/` che guida
un agente attraverso le 4 fasi: scoperta delle codelist, ricerca con filtri progressivi,
lettura del dettaglio, download delle risorse collegate (WMS/WFS/download).

## Riferimenti

- Pagina ufficiale REST API: <https://geodati.gov.it/geoportale/eng/strumenti-en/rest-api>
- Spec completa (sito di test Esri Geoportal Server, non produzione): <https://gpt.geocloud.com/geoportal3/api/gpt_api.json>
- Documentazione raccolta nella cartella [`ref/`](./ref).

## Licenza

MIT.
