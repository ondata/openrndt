# ISO 19115 — TopicCategoryCode

Categorie tematiche ammesse per il parametro `--data-category` di
`openrndt search`. Sono la stessa enumerazione del Codice ISO 19115
TopicCategoryCode usata da INSPIRE.

| Valore                              | Descrizione                                            |
|-------------------------------------|--------------------------------------------------------|
| `farming`                           | Agricoltura                                            |
| `biota`                             | Biota — flora e fauna naturali                          |
| `boundaries`                        | Confini amministrativi e legali                         |
| `climatologyMeteorologyAtmosphere`  | Climatologia, meteorologia, atmosfera                   |
| `economy`                           | Economia                                                |
| `elevation`                         | Altimetria, DTM/DEM                                     |
| `environment`                       | Ambiente, aree protette                                 |
| `geoscientificInformation`          | Informazioni geoscientifiche, geologia, pedologia       |
| `health`                            | Salute                                                  |
| `imageryBaseMapsEarthCover`         | Cartografia di base, ortofoto, copertura del suolo      |
| `intelligenceMilitary`              | Intelligence, difesa                                    |
| `inlandWaters`                      | Acque interne (fiumi, laghi, bacini)                    |
| `location`                          | Posizione (indirizzi, toponimi)                         |
| `oceans`                            | Oceani                                                  |
| `planningCadastre`                  | Pianificazione e catasto                                |
| `society`                           | Società                                                 |
| `structure`                         | Strutture (edifici, infrastrutture)                     |
| `transportation`                    | Trasporti (strade, ferrovie, porti)                     |
| `utilitiesCommunication`            | Utility e comunicazioni                                  |

## Uso

```bash
# singola categoria
openrndt search --data-category planningCadastre --num 10

# più categorie (separate da virgola, lato API)
openrndt search --data-category "planningCadastre,boundaries" --num 10
```

## Cheat sheet — dal bisogno alla categoria

| L'utente cerca…                      | Prova                                         |
|--------------------------------------|-----------------------------------------------|
| catasto, particelle, strumenti urbanistici | `planningCadastre`                       |
| confini comunali/provinciali/regionali     | `boundaries`                              |
| ortofoto, immagini satellitari, CLC         | `imageryBaseMapsEarthCover`               |
| fiumi, reticolo idrografico, alluvioni     | `inlandWaters`                            |
| strade, ferrovie, mobilità                  | `transportation`                          |
| DTM, DEM, modelli del terreno              | `elevation`                               |
| geologia, suolo, frane                      | `geoscientificInformation`               |
| aree protette, parchi, Natura 2000          | `environment`                             |
| edifici, infrastrutture                     | `structure`                               |
| reti elettriche/gas/acquedotto, telecomunicazioni | `utilitiesCommunication`            |

In dubbio fra due categorie: prova senza `--data-category` e usa solo `--q`,
poi guarda quale categoria ricorre nei `keywords_s` dei migliori risultati.
