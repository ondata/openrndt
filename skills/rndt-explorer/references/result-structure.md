# Struttura della risposta RNDT

Dettaglio dei payload restituiti da `openrndt search` (lista) e
`openrndt get` (dettaglio). Conoscere questi campi serve per estrarre
informazioni con `jq` e per costruire ricerche mirate via `q=campo:valore`.

## Response di `search` (formato JSON)

```text
{
  "start": 1, "num": 10, "total": 23580, "nextStart": 11,
  "sourceType": "Geoportal", "sourceKey": null,
  "results": [ Result… ]
}
```

`total` è un intero quando il match esiste. Se il campo richiesto in `q`
non è indicizzato, può tornare come oggetto `{value: 0, relation: "eq"}` —
significa zero risultati.

### Struttura `Result`

| Campo          | Tipo            | Contenuto                                                  |
|----------------|-----------------|-----------------------------------------------------------|
| `id`           | stringa         | identificativo univoco (es. `age:D_E973_MARSAGLIA`)         |
| `title`        | stringa         | titolo del metadato                                         |
| `description`  | stringa         | descrizione                                                 |
| `published`    | datetime ISO    | data di pubblicazione                                       |
| `updated`      | datetime ISO    | data di ultimo aggiornamento                                |
| `author`       | `{name}`        | autore della scheda                                         |
| `categories`   | `[ {scheme, term} ]` | parole chiave/categorie                              |
| `bbox`         | `{xmin,ymin,xmax,ymax}` | bounding box WGS84                                 |
| `links`        | array di link   | servizi e risorse correlate — vedi sotto                    |
| `_source`      | oggetto         | campi Elasticsearch indicizzati — vedi sotto                |

### Tabella `links`

| `rel`        | Significato                                          |
|--------------|------------------------------------------------------|
| `alternate`  | rappresentazione alternativa del metadato (JSON/HTML/XML) — ⚠️ **href inutilizzabile**, vedi sotto |
| `related`    | risorsa correlata; il `dctype` indica il tipo         |
| `enclosure`  | file scaricabile (di solito ZIP/GeoTIFF/PDF)          |

> ⚠️ **Non seguire gli href di `rel=alternate`.** Puntano a un indirizzo IP privato del server (`http://192.168.3.34:8080/geoportal-catalog/...`), irraggiungibile da qualunque client esterno. Vale per **tutti** i risultati di `search` (bug lato RNDT, issue #2 del repository).
>
> Per ottenere JSON, XML o HTML di un metadato usa i comandi dedicati, che costruiscono l'URL corretto:
>
> ```bash
> openrndt --format json get <id>     # JSON (_source completo)
> openrndt get <id> --xml             # XML ISO 19139
> openrndt get <id> --html            # HTML
> ```
>
> Se ti serve l'URL diretto (es. per un `curl` in uno script), sostituisci l'host: il percorso è già corretto e pubblicamente servito.
>
> ```
> ✗ http://192.168.3.34:8080/geoportal-catalog/rest/metadata/item/{id}/xml
> ✓ https://geodati.gov.it/geoportal-catalog/rest/metadata/item/{id}/xml
> ✓ https://geodati.gov.it/RNDT/rest/metadata/item/{id}/xml            (equivalente, usato dalla CLI)
> ```
>
> I due percorsi `/RNDT/` e `/geoportal-catalog/` sono alias dello stesso backend (verificato 2026-07-18: stessi conteggi, stesso comportamento di `sort`, stessi bug). L'XML ottenuto è **byte-identico** a quello del `GetRecordById` del CSW.

I `dctype` più comuni per `rel=related`:

| `dctype`     | Significato                                                  |
|--------------|--------------------------------------------------------------|
| `WMS`        | Web Map Service (OGC) — capabilities URL                      |
| `WFS`        | Web Feature Service (OGC)                                     |
| `WCS`        | Web Coverage Service (OGC)                                    |
| `WMTS`       | Web Map Tile Service                                          |
| `download`   | download diretto del dataset                                  |

Estrarre tutti i WMS dei primi 50 risultati di una ricerca:

```bash
openrndt --format json search --q "catasto" --num 50 \
  | jq -r '.results[].links[]
            | select(.dctype=="WMS") | .href' \
  | sort -u
```

Per evitare parsing manuale e fare anche health-check endpoint:

```bash
openrndt --format json resources <id>              # check singolo
openrndt --format json resources <id1> <id2>       # batch: {"count": N, "results": [per-id]}
openrndt --format json resources <id> --no-check   # solo estrazione URL
```

Campi del check per ogni endpoint (`resources --check`, default):

| Campo            | Contenuto                                                   |
|------------------|-------------------------------------------------------------|
| `type`           | WMS/WFS/WCS/WMTS/download dedotto dal link                  |
| `url`            | URL come da metadato                                        |
| `source`         | provenienza (`links`, `links_s`, `webServices_s`)           |
| `ok`             | True solo per la risposta **finale** 2xx                    |
| `status_code`    | status HTTP finale (es. 200)                                |
| `method`         | probe usata: `HEAD` o `GET` (fallback su 4xx/5xx a HEAD)    |
| `final_url`      | URL finale (dopo eventuali redirect)                        |
| `redirected`     | True se il probe ha seguito almeno un redirect              |
| `redirect_count` | numero di redirect seguiti (max 3)                          |
| `redirect_url`   | prima destinazione di redirect incontrata                   |
| `latency_ms`     | durata complessiva della probe (millisecondi)               |
| `error`          | motivo di fallimento: `url-blocked:…`, `redirect-blocked:…`, `too-many-redirects`, eccezione di rete |

Comportamenti verificati live: i redirect vengono seguiti **solo verso host
pubblici** — l'endpoint ARPA Veneto catalogato in `http` (301 verso `https`)
risulta `ok=true, redirected=true`; un 3xx verso un host non pubblico non viene
seguito ed espone `error=redirect-blocked:…`. In batch, un metadato
inesistente o irraggiungibile produce una voce con `error` senza fermare gli
altri.

## Campi `_source` più utili

`_source` contiene **tutti** i campi indicizzati Elasticsearch del metadato.
Questi sono i più ricorrenti e utili per costruire `q=campo:valore`:

| Campo                           | Cosa contiene                                                     |
|---------------------------------|-------------------------------------------------------------------|
| `title`                         | titolo del metadato                                               |
| `description`                   | descrizione testuale                                              |
| `fileid`                        | uguale al `id` del risultato                                      |
| `keywords_s`                    | parole chiave (include la categoria ISO 19115)                    |
| `INSPIRETheme_s`                | tema INSPIRE (es. `Idrografia`, `Trasporti`)                      |
| `contact_organizations_s`       | array di tutti gli enti responsabili                              |
| `apiso_OrganizationName_txt`    | nome completo dell'organizzazione principale                      |
| `EnteResponsabile_s`            | ente responsabile in forma breve (es. `Regione Siciliana`)        |
| `apiso_Type_s`                  | tipo di risorsa: `dataset`, `service`, ecc.                       |
| `PuntoDiContattoEmail_s`        | indirizzo email di contatto del responsabile                      |
| `PuntoDiContatto_s`             | nome del punto di contatto                                        |
| `PuntoDiContattoSitoWeb_s`      | sito web del punto di contatto                                    |
| `AmbitoTerritoriale_s`          | `Regionale`, `Nazionale`, `Locale`                                |
| `links_s`                       | URL dei servizi (WMS/WFS/download)                                |
| `webServices_s`                 | array dei servizi web esposti                                     |
| `bbox`                          | bounding box (anche dentro `_source`)                             |

> **`author.name` vs organizzazione**: `author.name` nel payload di ricerca è lo
> username di sistema (es. `agostino.cirasa`), non il nome dell'ente. Usa
> `_source.apiso_OrganizationName_txt` per il nome esteso.

> **Codice IPA**: non c'è un campo dedicato per il codice IPA dell'ufficio.
> Il prefisso dell'`id` prima dei due punti (es. `r_sicili` da `r_sicili:4e0a416f-...`)
> è il codice IPA dell'**ente capofila** (es. Regione Siciliana), non dell'ufficio
> specifico (es. Assessorato). Estraibile con `jq -r '.id | split(":")[0]'`.

Per esplorare un payload, prendi un risultato qualsiasi e fai:

```bash
openrndt --format json get <id> | jq '._source | keys'
```

## Response di `get`

Lo stesso oggetto in `results[*]` di una `search`, ma esposto al primo livello
con metadati Elasticsearch aggiuntivi: `_index`, `_id`, `_version`, `found`,
`_source`. La struttura di `_source` è identica.
