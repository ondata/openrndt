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

# Ordinamento per titolo (serve la direzione: `title` da solo dà errore)
openrndt search --q 'catasto' --sort 'title:asc' --num 5
```

## Cercare per data — si può, su tutti i campi

Distinzione fondamentale, verificata live il 2026-07-18: sul RNDT le date si **filtrano quasi sempre** e si **ordinano quasi mai**.

| Campo | Cosa è | Valorizzato | Filtrabile | Ordinabile |
|---|---|---|---|---|
| `apiso_Modified_dt` | dateStamp della **scheda** di metadati | 23.632 (100%) | ✅ | ✅ |
| `apiso_RevisionDate_dt` | revisione della risorsa | 13.276 (56%) | ✅ | ❌ |
| `apiso_CreationDate_dt` | creazione della risorsa | 10.138 (43%) | ✅ | ❌ |
| `apiso_PublicationDate_dt` | pubblicazione della risorsa | 8.402 (36%) | ✅ | ❌ |
| `timeperiod_nst[].begin_dt`/`end_dt` | copertura temporale del **dato** | parziale | solo via `--time` | ❌ |
| `sys_modified_dt` (= `updated` top-level del JSON grezzo, `indexed` negli output openrndt) | indicizzazione nel catalogo | 100% | ✅ | ✅ (inutile) |

> **Correzione**: una nota precedente dava `apiso_PublicationDate_dt` per "non indicizzato / inesistente". È falso: il campo c'è su 8.402 record e come filtro funziona. Quello che manca è solo l'ordinamento.

Il filtro si scrive come range Lucene dentro `--q` (timestamp completo, `Z` finale):

```bash
# Dataset sugli incendi creati dal 2024 a oggi
openrndt search --q 'incendi AND apiso_CreationDate_dt:[2024-01-01T00:00:00Z TO 2026-07-18T23:59:59Z]' --num 50

# Tutto ciò che è stato pubblicato nel 2024 (335 record)
openrndt search --q 'apiso_PublicationDate_dt:[2024-01-01T00:00:00Z TO 2024-12-31T23:59:59Z]' --num 1

# Aperto a destra
openrndt search --q 'apiso_RevisionDate_dt:[2024-01-01T00:00:00Z TO *]' --num 10
```

### La trappola della copertura parziale

Poiché i tre campi della risorsa sono compilati solo dal 36% al 56% dei record, **filtrare su un campo scarta in silenzio chi non ce l'ha**. Stessa ricerca "incendi" dal 2024 a oggi, al variare del campo:

| Filtro | Record |
|---|---|
| solo `apiso_CreationDate_dt` | 15 |
| solo `apiso_PublicationDate_dt` | 4 |
| solo `apiso_RevisionDate_dt` | 28 |
| **OR fra i tre** | **35** |
| `apiso_Modified_dt` (100% di copertura) | 63 |

Regola pratica: se la domanda è precisa ("creati nel 2024") filtra il campo giusto; se è larga ("cosa si è mosso dal 2024") usa l'OR:

```bash
Y='[2024-01-01T00:00:00Z TO 2026-07-18T23:59:59Z]'
openrndt search --num 50 \
  --q "incendi AND (apiso_CreationDate_dt:$Y OR apiso_PublicationDate_dt:$Y OR apiso_RevisionDate_dt:$Y)"
```

`apiso_Modified_dt` dà sempre il numero più alto perché è l'unico compilato ovunque, ma è la data della **scheda**: dice quando qualcuno ha toccato il record, non quando il dato è stato prodotto o pubblicato. Usalo come rete di sicurezza, non come misura della freschezza del dato.

> Lo stesso meccanismo, sbagliato, è il bug della Ricerca Dettagliata del portale web: mettendo in AND tutti e tre i campi data tiene solo i record che le hanno **tutte e tre** compilate, e arriva a mostrare 0 risultati dove ce ne sono 15.

### Ordinare per data: solo `apiso_Modified_dt`

Nessuno degli altri campi data è ordinabile: `sort=apiso_PublicationDate_dt:desc` e `:asc` restituiscono lo **stesso ordine** che si ottiene senza chiedere alcun ordinamento (parametro ignorato, non "ordine ascendente"). Idem per `apiso_RevisionDate_dt`.

Per ordinare per una data diversa da `apiso_Modified_dt`: filtra lato server e ordina lato client.

```bash
openrndt --format json search --q 'incendi AND apiso_CreationDate_dt:[2024-01-01T00:00:00Z TO *]' --num 50 \
  | jq -r '.results | sort_by(._source.apiso_CreationDate_dt) | reverse
           | .[] | "\(._source.apiso_CreationDate_dt[0:10])  \(.title)"'
```

**Trappola di verifica (solo `--format json`)**: dopo un sort per
`apiso_Modified_dt`, il campo top-level `updated` del JSON grezzo mostra la data
di indicizzazione, NON quella ordinata. Negli output `compact`/`csv`/`table` la
colonna `updated` è già `apiso_Modified_dt` (l'indicizzazione sta in `indexed`).
Sul JSON grezzo, per vedere la data vera:

```bash
openrndt search --q "catasto" --sort "apiso_Modified_dt:desc" --num 5 \
  | jq -r '.results[] | "\(._source.apiso_Modified_dt)  \(.title)"'
```

### Cosa ordina davvero — quadro completo (verificato 2026-07-18)

| `--sort` | Esito |
|---|---|
| `apiso_Modified_dt:asc\|desc` | ✅ ordina |
| `title:asc\|desc` | ✅ ordina alfabeticamente |
| `title` (senza direzione) | ❌ **errore** Elasticsearch *"Fielddata is disabled on [title]"* |
| `apiso_PublicationDate_dt:*`, `apiso_RevisionDate_dt:*` | ❌ ignorati (ordine = default) |
| `dateDescending`, `dateAscending`, `relevance` | ❌ ignorati (ordine = default) |

> Attenzione: `relevance` e `title` (nudo) sono elencati come validi nella [documentazione ufficiale](https://geodati.gov.it/geoportale/strumenti/api-rest), ma il primo non ha effetto e il secondo dà errore. La forma funzionante `campo:asc|desc` non è invece documentata. Il menu "ORDINA PER" del portale offre esattamente le due sole coppie che funzionano (`title` e `apiso_Modified_dt`).

Altri limiti:

- Il servizio **CSW** (`/csw`) ignora del tutto `<ogc:SortBy>` pur dichiarando `CoreSortables: Title, Modified` nel GetCapabilities: non ordina per nessuna proprietà. Dettagli e implicazioni INSPIRE in [`csw.md`](./csw.md) e `ref/csw-rndt.md`.
- I campi *garantiti* sortable restano quelli `_s`/`_dt`/`_i`: su altri campi text non c'è garanzia.

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

## Zero risultati — la CLI suggerisce

`openrndt search` con `total=0` stampa su stderr suggerimenti contestuali:
allargare il testo con wildcard, rimuovere `--data-category`/`--time`/`--bbox`,
e per gli enti usare il nominativo esatto. Non è rumore: sono le cause
verificate più frequenti del falso zero.

Tre casi ricorrenti, tutti verificati live:

1. **Periodo legittimamente vuoto.** `--time 2015-01-01/2024-12-31
   --data-category inlandWaters` → 42; `--time 2024-01-01/2024-12-31` sulla
   stessa query può dare numeri molto più bassi perché in quel periodo quei
   record non esistono. Allarga l'intervallo prima di sospettare un bug.
2. **Ente non indicizzato col proprio nominativo.** Il Comune di Bologna dà 0
   sia con `apiso_OrganizationName_txt:"Comune di Bologna"` sia con
   `EnteResponsabile_s:"Comune di Bologna"` e il prefisso IPA `c_a944*`
   (riverificato 2026-08-29: ancora 0 su tutte e tre le forme): i suoi prodotti
   entrano in catalogo tramite regione o città metropolitana. La sequenza da
   seguire è in «Cercare i dati di un ente che non pubblica in proprio» nella
   SKILL: gli enti suggeriti dalla CLI, poi il nome del territorio come frase
   esatta (`--q '"Comune di Bologna"'` → 13 record, tutti pertinenti), poi il
   nome del territorio con la bbox o con l'ente sovraordinato.
   **Da evitare** `contact_organizations_s:*Bologna*`: dà 110 record e nessuno è
   del Comune (sono di Regione Emilia-Romagna, Città metropolitana, ARSTPC e
   ARPAE, che spesso quel territorio lo nominano solo perché ci hanno sede), ed
   è case-sensitive (`*bologna*` → 0). **Da evitare** anche
   `AmbitoTerritoriale_s:Locale` con la bbox: `Locale` copre 41 record su 3000 e
   la bbox lascia passare i record a estensione nazionale.
3. **Bbox ristretta.** Il filtro è per sovrapposizione, ma molti record
   dichiarano bbox nazionali/globali: con un riquadro stretto si escludono in
   silenzio. Se la domanda è «cosa copre la mia area», allarga il riquadro e
   affina dopo.

## Suggerimenti

- Termini con apostrofo: usa virgolette, es. `"d'Aosta"`.
- UTF-8 e accenti funzionano direttamente: `idrografia`, `città`.
- Per imparare la sintassi: usa la [Ricerca
  Dettagliata](https://geodati.gov.it/geoportale/) del portale web, applica i
  filtri desiderati e copia l'URL dei risultati.
- Per filtrare per categoria ISO 19115 **non usare la query string
  `dataCategory`** (non funziona, vedi `ref/rest-api-rndt.md`): usa il flag
  CLI `--data-category` oppure direttamente `q=keywords_s:VAL`.
