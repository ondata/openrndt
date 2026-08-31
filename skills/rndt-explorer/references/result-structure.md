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
| `updated`      | datetime ISO    | **indicizzazione nel catalogo** (= `_source.sys_modified_dt`), non la data della scheda: quella è `_source.apiso_Modified_dt`. Negli output `compact`/`csv`/`table` di openrndt i due campi si chiamano rispettivamente `indexed` e `updated` |
| `author`       | `{name}`        | autore della scheda                                         |
| `categories`   | `[ {scheme, term} ]` | parole chiave/categorie                              |
| `bbox`         | `{xmin,ymin,xmax,ymax}` | bounding box WGS84                                 |
| `links`        | array di link   | servizi e risorse correlate — vedi sotto                    |
| `_source`      | oggetto         | campi Elasticsearch indicizzati — vedi sotto                |

### Tabella `links`

| `rel`        | Significato                                          |
|--------------|------------------------------------------------------|
| `alternate`  | rappresentazione alternativa del metadato (JSON/HTML/XML); quello `type=text/html` è il permalink della scheda (campo `url` di `compact`) |
| `related`    | risorsa correlata; il `dctype` indica il tipo         |
| `enclosure`  | file scaricabile (di solito ZIP/GeoTIFF/PDF)          |

> **Nota storica.** Fino all'estate 2026 gli href di `rel=alternate` puntavano a un IP privato del server (`http://192.168.3.34:8080/...`), irraggiungibile dall'esterno (issue #2 del repository, segnalata al RNDT). Dal 2026-08-29 il bug è corretto: su 600 link di 200 risultati tutti gli host sono `https://geodati.gov.it`. Gli href sono quindi usabili e il permalink `text/html` è quello che la CLI espone come `url`. Se in futuro dovessi rivedere un IP privato, la cura è la stessa di allora: sostituire l'host.
>
> Per ottenere JSON, XML o HTML di un metadato i comandi dedicati restano la via più comoda:
>
> ```bash
> openrndt --format json get <id>     # JSON (_source completo)
> openrndt get <id> --xml             # XML ISO 19139
> openrndt get <id> --html            # HTML
> ```
>
> URL diretti equivalenti, per un `curl` in uno script:
>
> ```
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

Dalla 3.3.0 `get` con `--format json` (default) restituisce un **documento
normalizzato** costruito da `_source`, con lo stesso vocabolario delle risposte
di `search` più i dettagli utili alla scheda. `_source` e i flag della busta
(`_index`, `_id`, `_version`, `found`, …) sono preservati inalterati in coda.

| Campo              | Contenuto                                                  |
|--------------------|------------------------------------------------------------|
| `id`               | identificativo del record (`_source.fileid`)               |
| `title`, `description` | titolo e descrizione                                   |
| `org`              | ente responsabile (`apiso_OrganizationName_txt` o `EnteResponsabile_s`) |
| `type`, `category` | tipo risorsa (`apiso_Type_s`) e categoria ISO 19115           |
| `updated`          | data della **scheda** (`apiso_Modified_dt`), come in `compact` |
| `indexed`          | indicizzazione nel catalogo (`sys_modified_dt`)               |
| `data_date`        | data del **dato** (`apiso_RevisionDate_dt`, poi Creation/Publication) |
| `open`, `license`  | come in `compact` (isOpendata e licenza dichiarata, non normalizzate) |
| `contact`          | `{name, email, website}` del punto di contatto designato (`PuntoDiContatto*`) |
| `bbox`             | `{xmin,ymin,xmax,ymax}` ricavato da `envelope_geo`            |
| `lineage`          | provenienza/qualità del dato (`apiso_Lineage_txt`)            |
| `resources`        | risorse fruibili come `resources --no-check` (vedi sotto)     |
| `url`              | permalink citabile della scheda (`…/rest/metadata/item/{id}/html`) |

La busta Elasticsearch grezza resta disponibile con `--raw` (comportamento
ante 3.3.0), per chi lavora direttamente sui campi indicizzati:

```bash
openrndt --format json get ispra_rm:01CLCALL_SDT | jq '.contact.email, .data_date, .bbox'
openrndt get ispra_rm:01CLCALL_SDT --raw | jq '._source | keys'
```

## Campi del check di `resources`

`openrndt --format json resources <id>` restituisce per ogni risorsa `type`,
`url`, `source` e, quando il check è attivo, gli esiti della probe. Attenzione:
qui le chiavi sono `type`/`url`, mentre in `links[]` di `search`/`get` le stesse
informazioni stanno in `dctype`/`href`.

| Campo | Significato |
|---|---|
| `ok` / `status_code` | esito della probe sul GetCapabilities (o sull'URL del file). `ok=true` non prova che un WMS sappia disegnare: vedi `ogc-services.md` |
| `final_url` / `redirect_url` | ultimo URL contattato e prima destinazione di redirect |
| `redirected` / `redirect_count` | i redirect sono seguiti solo verso host pubblici; verso loopback, IP privati o DNS riservati si fermano con `error=redirect-blocked:…` (un endpoint `http` che rimanda al proprio `https`, es. `gaia.arpa.veneto.it`, risulta quindi `ok=true`) |
| `latency_ms` | durata complessiva della probe: distingue un servizio veloce da uno che risponde 200 ma lento |
| `error` | tipo dell'eccezione. Se è di rete, riprova con `curl -sI`: fino alla CLI 3.1.0 i server con TLS legacy davano `ConnectError` pur rispondendo |
| `method` | `HEAD` o `GET`: la probe prova HEAD e ripiega su GET in streaming |

Con più ID l'output è `{"count": N, "results": [per-id]}` e un metadato mancante
produce una voce con `error` senza interrompere gli altri; con un solo ID resta
il formato storico.

