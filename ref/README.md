# ref/ — documentazione API raccolta

Risorse di riferimento per il RNDT.

## File

- **`rest-api-rndt.md`** — sintesi in italiano della pagina ufficiale
  <https://geodati.gov.it/geoportale/eng/strumenti-en/rest-api>. Parametri, valori validi,
  formati output, 6 esempi ufficiali, endpoint dettaglio.

- **`gpt_api.json`** — Swagger 2.0 (~49 KB) dell'engine sottostante (Esri Geoportal
  Server v3.0.1). **Non è l'API del RNDT in produzione**: è il sito di test del prodotto
  Esri Geoportal Server raggiungibile da <https://gpt.geocloud.com/geoportal3/>. Lo
  conserviamo perché la sintassi degli endpoint è la stessa e la spec elenca
  funzionalità non documentate sulla pagina italiana (autenticazione OAuth, CSW, OGC
  Records, endpoint admin). Per il RNDT pubblico usare sempre la base URL ufficiale:
  `https://geodati.gov.it/RNDT`.

- **`sample-search-response.json`** — risposta JSON reale ottenuta da
  `GET https://geodati.gov.it/RNDT/rest/metadata/search?q=*&f=json&num=2` (acquisita
  2026-05-27, totale catalogo: 23.580 record).

## Differenza geodati.gov.it vs gpt.geocloud.com

| Host                          | Ruolo                                                          |
|-------------------------------|----------------------------------------------------------------|
| `geodati.gov.it/RNDT`         | API REST del RNDT italiano in produzione (catalogo reale).      |
| `gpt.geocloud.com/geoportal3` | Sito demo di Esri Geoportal Server (dati di test, non RNDT).    |

Entrambi sono istanze dello stesso prodotto: la sintassi `/rest/metadata/...` è
identica, ma i dati e l'amministrazione sono separati.
