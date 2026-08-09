# API REST RNDT — documentazione ufficiale (versione italiana)

Pagina di origine: <https://geodati.gov.it/geoportale/strumenti/api-rest>
Data pagina: 12/01/2026 · **Ultima modifica dichiarata: 29/05/2026**
Copia acquisita: 2026-07-17

> Mirror fedele della pagina ufficiale italiana. Le divergenze fra quanto qui documentato e il comportamento reale dell'API sono raccolte in `tmp/bugs-incoerenze.md` e nelle issue del repository. La copia inglese, acquisita il 2026-06-10, è in `rest-api-rndt.md`.

## Accesso ai dati tramite API REST

La ricerca dei dati nel RNDT è possibile anche tramite API REST. Per interrogare il Catalogo, l'URL da utilizzare è il seguente:

```
https://geodati.gov.it/RNDT/rest/metadata/search?<parametro>&<parametro>&…
```

dove `<parametro>` è uno dei parametri REST disponibili. Di seguito sono elencati quelli principali.

| Parametro | Descrizione | Valori accettati |
|---|---|---|
| `bbox` | Estensione indicata come due coppie di coordinate (ovest-sud e est-nord). | Valori di latitudine e longitudine separati da virgole. |
| `q` | Testo. | Stringa. È possibile comporre la stringa di ricerca utilizzando tutti gli elementi indicizzati (vedi dopo), wildchars e operatori booleani. |
| `dataCategory` | Categoria tematica del dataset, definita nello Standard ISO 19115 (enumerazione TopicCategoryCode). | Valori separati da virgola. |
| `time` | Date per identificare un intervallo temporale. | Inizio/fine entrambe date nel formato `yyyy-mm-dd`. |
| `sort` | Ordinamento risultati. | Uno fra: `dateAscending`, `dateDescending` (default), `relevance`, `title`. |
| `start` | Numero del primo record da considerare. | Intero. Se utilizzato insieme al parametro `max`, fornisce l'impaginazione dei risultati. |
| `num` | Numero massimo di risultati. | Intero. Valore massimo: 5000, default: 10. Se utilizzato insieme al parametro `start`, fornisce l'impaginazione. |
| `f` | Formato della risposta. | Un valore fra: `atom`, `json`, `csw`, `rss`, `csv`, `kml`, `eros`, `json-source`. |

Per maggiori dettagli la pagina rimanda alla "REST API Syntax" del **sito di test** del geoportal-server (`gpt.geocloud.com`).

Il motore di ricerca è basato su Elasticsearch, che a sua volta utilizza Apache Lucene. Per sfruttare al meglio la ricerca può essere utile conoscere la sintassi delle query Apache Lucene.

> **Elementi interrogabili** (citazione): «Gli elementi interrogabili da utilizzare nelle ricerche nel RNDT sono visualizzabili nella risposta JSON interrogando un qualunque metadato; essi includono i criteri di ricerca indicati nelle linee guida INSPIRE sui servizi di ricerca. Per esempi di uso è possibile utilizzare la Ricerca Dettagliata impostando i filtri di interesse, poi sulla pagina di Anteprima cliccare sul simbolo del link e copiare e incollare il testo in un browser.»

### Esempi riportati dalla pagina

**Esempio 1** — dati con tema INSPIRE Idrografia, primi 300 record, output JSON. La descrizione parla di «ordinamento basato sul titolo», ma l'URL non contiene alcun parametro `sort`:

```
https://geodati.gov.it/RNDT/rest/metadata/search?q=INSPIRETheme_s:Idrografia&start=1&num=300&f=json
```

**Esempio 2** — parole "carta" e "geologica" nel titolo. La descrizione cita `sort=title`, assente dagli URL:

```
https://geodati.gov.it/RNDT/rest/metadata/search?q=title:"carta geologica"&start=20&num=50&f=html
https://geodati.gov.it/RNDT/rest/metadata/search?q=(title:carta geologica)&start=20&num=50&f=html
https://geodati.gov.it/RNDT/rest/metadata/search?q=title:(carta AND geologica)&start=20&num=50&f=html
```

Spiegazione fornita: con le virgolette si cerca la frase esatta; senza, la seconda parola è cercata in qualunque campo perché «quando non specificato, il criterio di default è `text`»; con `AND` si cercano entrambe le parole non necessariamente contigue.

**Esempio 3** — wildcard e operatori di inclusione/esclusione. La descrizione cita `sort=title:desc`, assente dagli URL:

```
https://geodati.gov.it/RNDT/rest/metadata/search?q=(suolo -natura)&start=1&num=50&f=json
https://geodati.gov.it/RNDT/rest/metadata/search?q=(*suo%20-na??ra)&start=1&num=50&f=json
```

**Esempio 4** — record specifico tramite ID; la pagina dichiara che «ritorna l'XML del metadato»:

```
https://geodati.gov.it/RNDT/rest/metadata/search?id=ispra_rm:0029CNATHB_DT
```

## Contatti indicati dal portale

AgID — Agenzia per l'Italia Digitale, Via Liszt 21, 00144 Roma. Chat Skype: `rndt.help`; email: `info@rndt.gov.it` (nel sito è offuscata anti-spam).

## Divergenze note rispetto al comportamento reale

Verificate live il 2026-07-17; dettaglio in `tmp/bugs-incoerenze.md`.

| Documentato qui | Comportamento reale |
|---|---|
| `sort`: `dateAscending`, `dateDescending` (default), `relevance`, `title` | **Tutti e quattro non funzionano**: `dateAscending`/`dateDescending`/`relevance` sono ignorati (ordine = default); `sort=title` nudo restituisce errore Elasticsearch «Fielddata is disabled on [title]». L'unica sintassi funzionante è `campo:asc\|desc` (non documentata), e solo su `apiso_Modified_dt` e `title` (es. `sort=title:asc`). |
| `dataCategory` filtra per categoria ISO 19115 | Non filtra: restituisce sempre il catalogo intero, senza errore. Filtro reale: `q=keywords_s:VALORE`. |
| `f`: `atom, json, csw, rss, csv, kml, eros, json-source` | Tutti rispondono HTTP 200. `html` non è elencato ma è usato negli esempi della pagina stessa; per `search`, `f=html` e `f=xml` restituiscono in realtà `application/atom+xml`. |
| `start` «insieme al parametro `max`» | La tabella documenta `num`, il testo cita `max`: entrambi accettati dall'endpoint. |
| Gli esempi descrivono un ordinamento | Gli URL degli esempi non contengono il parametro `sort`. |
| «usare la Ricerca Dettagliata → Anteprima → copiare il link» | Il link copiato punta all'IP interno `http://192.168.3.34:8080/…`, irraggiungibile dall'esterno (issue #2). Il percorso ufficialmente consigliato per imparare la sintassi produce quindi un URL non funzionante. |
