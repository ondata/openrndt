# Endpoint GeoDCAT-AP del RNDT — documentazione ufficiale

Pagina di origine: <https://geodati.gov.it/geoportale/strumenti/endpoint-geodcat-ap>
Endpoint: <https://geodati.gov.it/geodcat-ap_it/> (applicazione: `index.php`)
Copia acquisita: 2026-07-17

> Strumento ufficiale che **non era presente in questo archivio**. Rilevante per openrndt: è la via ufficiale per ottenere i metadati RNDT in RDF/JSON-LD secondo DCAT-AP_IT, potenzialmente con la licenza espressa in modo normalizzato (`dct:license`), a differenza del campo licenza incoerente dell'API REST.

## Cosa dichiara la pagina ufficiale

L'API del RNDT per l'implementazione di GeoDCAT-AP consente di trasformare i metadati documentati nel Repertorio, secondo il profilo italiano, dallo standard ISO TS 19139 agli standard DCAT-AP / DCAT-AP_IT (estensione italiana di DCAT-AP) e GeoDCAT-AP(_IT), usati per i dati aperti.

L'API è basata sulle Linee Guida nazionali per l'implementazione di GeoDCAT-AP, declinazione italiana della specifica europea, e serve a rendere disponibili le descrizioni dei dati territoriali aperti anche attraverso portali generalisti come **dati.gov.it**, senza oneri aggiuntivi per le amministrazioni.

Dalla pagina dell'applicazione:

> «L'API accetta sia richieste CSW (GET e POST) che richieste REST e restituisce i metadati in formato RDF/XML o JSON-LD.»

## Parametri dell'interfaccia

| Opzione | Valori |
|---|---|
| Trasformazione di output (GET) | `geodcatap_it` (GeoDCAT-AP_IT), `dcatap_it` (DCAT-AP_IT), `core` (DCAT-AP), `extended` (GeoDCAT-AP) |
| Trasformazione di output (POST) | `geodcatap_it`, `dcatap_it` |
| Formato di input | CSW, REST |
| Formato di output | `application/rdf+xml`, `application/ld+json` |

## Riferimenti indicati dalla pagina

- Codice sorgente AgID (riuso): <https://github.com/AgID/rndt-geodcat-ap-api>
- API originale JRC/SEMIC da cui deriva: <https://github.com/SEMICeu/iso-19139-to-dcat-ap/tree/master/api>
- Linee guida GeoDCAT-AP_IT v1.0 (PDF): <https://geodati.gov.it/geoportale/images/struttura/documenti/GeoDCAT-AP_IT-v1.0.pdf>
- Interview on GeoDCAT-AP — Agency for Digital Italy (ISA²)
- Webinar "GeoDCAT-AP: Adoption and implementation experiences…" (Joinup)
- Webinar "Dati territoriali e dati aperti: il nuovo endpoint GeoDCAT-AP del RNDT"

## Stato della verifica (2026-07-17) — da completare

- L'endpoint base risponde `HTTP 200` e serve un form HTML (`index.php`).
- Le chiamate GET provate con i parametri del progetto SEMIC (`src=<URL XML>`, `outputSchema=geodcatap_it`, `format=application/rdf+xml`), sia con sorgente REST (`/RNDT/rest/metadata/item/{id}/xml`) sia con sorgente CSW (`GetRecordById`), hanno restituito **corpo vuoto**. La sintassi esatta non è ancora stata determinata: il form probabilmente invia in POST, oppure usa nomi di parametro diversi.
- La sorgente CSW `GetRecordById` è raggiungibile e restituisce l'ISO 19139 completo (≈37 KB), quindi il problema è nella chiamata all'API di trasformazione, non nel metadato di origine.

**Da fare**: leggere la guida online dell'applicazione o il codice in `AgID/rndt-geodcat-ap-api` per ricavare i nomi esatti dei parametri, poi verificare se `dct:license` restituisce la licenza normalizzata anche per i record in cui l'API REST la espone solo in `apiso_OtherConstraints_s` (es. i dataset AIB del MASE). Se sì, è la via consigliata per ottenere licenze affidabili.
