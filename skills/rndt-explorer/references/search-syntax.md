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

## Esempi verificati live

```bash
# Tema INSPIRE
openrndt search --q 'INSPIRETheme_s:Idrografia' --num 5         # → 845 totali

# Ente (forma breve)
openrndt search --q 'contact_organizations_s:"Agenzia delle Entrate"' --num 5

# Ente (nome completo — più preciso)
openrndt search --q 'apiso_OrganizationName_txt:"Regione Siciliana - Assessorato del Territorio e dell'\''Ambiente"' --num 5

# Ultimi 5 per ente, ordinati per data
openrndt search --q 'apiso_OrganizationName_txt:"Regione Siciliana"' --sort dateDescending --num 5

# Solo dataset (esclude servizi)
openrndt search --q 'apiso_OrganizationName_txt:"Regione Siciliana" AND apiso_Type_s:dataset' --num 10

# Trovare l'username di un autore e ricavare il codice IPA
openrndt search --q 'apiso_OrganizationName_txt:"Regione Siciliana"' --num 1 \
  | jq -r '.results[0] | {autore: .author.name, codice_ipa: (.id | split(":")[0])}'

# Combinazione: catasto OR cartografia, escluso "test"
openrndt search --q '(catasto OR cartografia) -test' --num 10

# Frase esatta nel titolo
openrndt search --q 'title:"carta geologica"' --num 5            # → 154 totali

# Wildcard
openrndt search --q 'title:*alluvion*' --num 10

# Filtro temporale (parametro dedicato, NON dentro q)
openrndt search --time "2024-01-01/2024-12-31" --num 10
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
