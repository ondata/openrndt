# Sintassi del parametro `--q`

Il parametro `--q` di `openrndt search` accetta query Lucene/Elasticsearch.
La pagina ufficiale rimanda alla [Apache Lucene Query Parser
Syntax](https://lucene.apache.org/core/2_9_4/queryparsersyntax.html).

## Operatori principali

| Operatore         | Significato                                       | Esempio                                     |
|-------------------|---------------------------------------------------|---------------------------------------------|
| spazio            | OR implicito                                       | `catasto urbano`                            |
| `AND`             | entrambi i termini                                 | `title:(carta AND geologica)`               |
| `OR`              | almeno uno dei termini                             | `WMS OR WFS`                                |
| `NOT` o `-`       | esclusione                                         | `suolo -natura`                             |
| `"..."`           | frase esatta                                       | `title:"carta geologica"`                   |
| `*`               | zero o più caratteri (wildcard)                    | `*suolo*`                                   |
| `?`               | esattamente un carattere                           | `na??ra`                                    |
| `field:value`     | restringe a un campo specifico                     | `INSPIRETheme_s:Idrografia`                 |
| `field:(a AND b)` | combina su uno stesso campo                        | `title:(carta AND geologica)`               |

## Campi più utili

Lista completa in [`result-structure.md`](./result-structure.md). I più ricorrenti:

- `title`
- `description`
- `keywords_s` (qui finisce anche la categoria ISO 19115)
- `INSPIRETheme_s` (tema INSPIRE)
- `contact_organizations_s` (array di enti — cerca con wildcard)
- `apiso_OrganizationName_txt` (nome completo organizzazione — più preciso per ricerche esatte)
- `EnteResponsabile_s` (ente responsabile, forma breve)
- `apiso_Type_s` (tipo risorsa: `dataset`, `service`, ecc.)
- `PuntoDiContattoEmail_s` (email contatto)
- `AmbitoTerritoriale_s` (Regionale/Nazionale/Locale)
- `isOpendata` (licenza open data: `isOpendata:*` per tutti gli open data)
- `apiso_CRS` (sistema di riferimento, es. `apiso_CRS:"EPSG:4326"` — utile per operatori GIS)
- `apiso_Format_s` (formati disponibili, es. `Shapefile`, `GeoTIFF`, `GML`)

## Esempi verificati live

```bash
# Tema INSPIRE
openrndt search --q 'INSPIRETheme_s:Idrografia' --num 5         # → 863 totali (2026-07-17)

# Ente (forma breve)
openrndt search --q 'contact_organizations_s:"Agenzia delle Entrate"' --num 5

# Ente (nome completo — più preciso)
openrndt search --q 'apiso_OrganizationName_txt:"Regione Siciliana - Assessorato del Territorio e dell'\''Ambiente"' --num 5

# Ultimi 5 per ente, ordinati per data (dateDescending NON ordina: usa apiso_Modified_dt:desc)
openrndt search --q 'apiso_OrganizationName_txt:"Regione Siciliana"' --sort 'apiso_Modified_dt:desc' --num 5

# Solo dataset (esclude servizi)
openrndt search --q 'apiso_OrganizationName_txt:"Regione Siciliana" AND apiso_Type_s:dataset' --num 10

# Ricavare il codice IPA dell'ente capofila (non dell'ufficio specifico)
openrndt search --q 'apiso_OrganizationName_txt:"Regione Siciliana"' --num 1 \
  | jq -r '.results[0] | {autore: .author.name, codice_ipa_ente: (.id | split(":")[0])}'

# Combinazione: catasto OR cartografia, escluso "test"
openrndt search --q '(catasto OR cartografia) -test' --num 10

# Frase esatta nel titolo
openrndt search --q 'title:"carta geologica"' --num 5            # → 154 totali

# Wildcard
openrndt search --q 'title:*alluvion*' --num 10

# Filtro temporale (parametro dedicato, NON dentro q)
openrndt search --time "2024-01-01/2024-12-31" --num 10
```

## Ordinamento (`--sort`) — attenzione

Verificato live: i valori `dateDescending`/`dateAscending` documentati
**non ordinano** (RNDT restituisce ordine identico fra i due → ignorati).
Il meccanismo reale è la sintassi Elasticsearch `campo:asc|desc` su un campo
*sortable* (keyword `_s`, data `_dt`, intero `_i`).

```bash
# Ultimi metadati per data di modifica scheda (proxy migliore per "più recenti")
openrndt search --q 'EnteResponsabile_s:"Regione Siciliana"' --sort 'apiso_Modified_dt:desc' --num 5

# Crescente
openrndt search --q 'apiso_Type_s:dataset' --sort 'apiso_Modified_dt:asc' --num 5

# Pertinenza (funziona)
openrndt search --q 'catasto' --sort 'relevance' --num 5
```

### Quale data stai ordinando (importante)

Sul RNDT convivono più date, e quella "giusta" per l'utente spesso non esiste:

| Campo | Cosa è | Ordinabile? |
|---|---|---|
| `_source.apiso_Modified_dt` | dateStamp della **scheda di metadati** | ✅ — il miglior proxy per "più recenti" |
| data di pubblicazione dei dati | solo nell'XML ISO (`dateType=publication`), **non indicizzata** | ❌ non esiste come campo |
| `_source.apiso_CreationDate_dt` | creazione della risorsa | spesso `null` o fittizia (`2012-01-01`): inaffidabile |
| `updated` (top-level nei risultati) | **reindicizzazione del catalogo** | non è il campo su cui ordini |

Quindi: `apiso_Modified_dt:desc` ordina per data di modifica della *scheda*,
non dei *dati* — dillo all'utente quando presenti i risultati come "più recenti".

**Trappola di verifica**: dopo un sort per `apiso_Modified_dt`, il campo
`updated` che vedi nei risultati (e nell'output `compact`) mostra la data di
reindex, NON quella ordinata. Per vedere la data vera:

```bash
openrndt search --q "catasto" --sort "apiso_Modified_dt:desc" --num 5 \
  | jq -r '.results[] | "\(._source.apiso_Modified_dt)  \(.title)"'
```

Limiti noti:

- Il sort su `title` (campo text) in passato dava errore Elasticsearch
  *"Fielddata is disabled"*; **riverificato il 2026-07-17: ora funziona**
  (`title:asc` ordina alfabeticamente — il comportamento dell'API è cambiato).
  I campi *garantiti* sortable restano comunque quelli `_s`/`_dt`/`_i`:
  su altri campi text non c'è garanzia.
- Il servizio **CSW** (`/csw`) ignora del tutto `<ogc:SortBy>`: non ordina per
  nessuna proprietà. Dettagli e implicazioni INSPIRE in `ref/rest-api-rndt.md`.

## Filtrare per ente — usa la forma stabile

Lo stesso ente compare con molte varianti del nome lungo in
`apiso_OrganizationName_txt` (uffici/dipartimenti diversi). Filtrare per la
stringa esatta lunga è fragile e perde record. Preferisci la forma breve
`EnteResponsabile_s` o il prefisso dell'`id` (codice IPA dell'ente capofila):

```bash
# Robusto: forma breve dell'ente
openrndt search --q 'EnteResponsabile_s:"Regione Siciliana"' --sort 'apiso_Modified_dt:desc' --num 5

# Robusto: per prefisso id (codice IPA ente capofila)
openrndt search --q 'apiso_Identifier_s:r_sicili*' --sort 'apiso_Modified_dt:desc' --num 5
```

## Suggerimenti

- Termini con apostrofo: usa virgolette, es. `"d'Aosta"`.
- UTF-8 e accenti funzionano direttamente: `idrografia`, `città`.
- Per imparare la sintassi: usa la [Ricerca
  Dettagliata](https://geodati.gov.it/geoportale/) del portale web, applica i
  filtri desiderati e copia l'URL dei risultati.
- Per filtrare per categoria ISO 19115 **non usare la query string
  `dataCategory`** (non funziona, vedi `ref/rest-api-rndt.md`): usa il flag
  CLI `--data-category` oppure direttamente `q=keywords_s:VAL`.
