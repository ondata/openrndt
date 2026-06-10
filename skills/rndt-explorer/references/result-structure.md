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
| `alternate`  | rappresentazione alternativa del metadato (JSON/HTML/XML) |
| `related`    | risorsa correlata; il `dctype` indica il tipo         |
| `enclosure`  | file scaricabile (di solito ZIP/GeoTIFF/PDF)          |

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

## Campi `_source` più utili

`_source` contiene **tutti** i campi indicizzati Elasticsearch del metadato.
Questi sono i più ricorrenti e utili per costruire `q=campo:valore`:

| Campo                       | Cosa contiene                                  |
|-----------------------------|------------------------------------------------|
| `title`                     | titolo del metadato                            |
| `description`               | descrizione testuale                           |
| `fileid`                    | uguale al `id` del risultato                   |
| `keywords_s`                | parole chiave (include la categoria ISO 19115) |
| `INSPIRETheme_s`            | tema INSPIRE (es. `Idrografia`, `Trasporti`)   |
| `contact_organizations_s`   | enti responsabili del dato                     |
| `AmbitoTerritoriale_s`      | `Regionale`, `Nazionale`, `Locale`             |
| `links_s`                   | URL dei servizi (WMS/WFS/download)             |
| `webServices_s`             | array dei servizi web esposti                  |
| `bbox`                      | bounding box (anche dentro `_source`)          |

Per esplorare un payload, prendi un risultato qualsiasi e fai:

```bash
openrndt --format json get <id> | jq '._source | keys'
```

## Response di `get`

Lo stesso oggetto in `results[*]` di una `search`, ma esposto al primo livello
con metadati Elasticsearch aggiuntivi: `_index`, `_id`, `_version`, `found`,
`_source`. La struttura di `_source` è identica.
