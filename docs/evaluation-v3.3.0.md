# Evaluation del triggering della descrizione

Data 2026-08-31, skill rndt-explorer v3.3.0. Obiettivo: misurare se la descrizione trigghera solo per richieste sensate e portare a una scelta documentata.

## Metodo

- Dataset di 21 query (10 positive, 11 negative) in skills/rndt-explorer/evals/trigger-evals.json, riviste e approvate una a una. Le negative sono quasi-raggiungimenti verso le skill concorrenti davvero installate: geolibre, portolan, ckan-explorer, istat-mcp, situas-explorer, sdmx-explorer, open-data-quality, ipa, datawrapper.
- Ogni query eseguita 3 volte; la skill conta come triggherata se lo è in almeno 2 run su 3. Giudice: il modello di sessione (zai/glm-5.3-flash) con in contesto le descrizioni reali delle nove concorrenti più quella sotto test, cioè lo stesso meccanismo con cui l'harness decide il trigger. Template del prompt in skills/rndt-explorer/evals/trigger-judge-prompt.txt.
- Holdout di 6 query nuove (3 positive, 3 negative sugli stessi assi di fallimento), mai usate nell'iterazione, per controllare l'overfitting.

## Risultati

| Descrizione | Set principale (21 query) | Holdout (6 query) |
|---|---|---|
| Precedente (prima della modifica) | accuracy 90,5%: recall 10/10, 2 falsi positivi su 11 | accuracy 83,3%: 1 falso positivo su 3 negativi |
| V2 (applicata) | accuracy 100%: recall 10/10, 0 falsi positivi, tutti i casi a 3/3 o 0/3 | accuracy 100%: 6/6 |

Fallimenti della descrizione precedente:

- Geoportale regionale da sfogliare (3/3 falsi positivi, ripresentato su holdout con la Sardegna): la frase "servizi WMS/WFS regionali e nazionali" viene letta come "ti guida nell'esplorazione di geoportali regionali".
- Corine Land Cover europeo da ritagliare sull'Italia (2/3): manca un confine esplicito sui geodati extra-italiani.

## Scelta

Applicata la V2: stesso impianto della descrizione che aveva recall pieno, con tre aggiunte. Lo scope dichiarato è il catalogo nazionale dei metadati geografici (ISO 19115/INSPIRE); i servizi regionali sono qualificati come indicizzati in questo catalogo nazionale; c'è un elenco di non-goal (geodati non italiani, statistiche senza geometrie, elaborazione di file GIS già in mano, mappe da dati già disponibili, portali CKAN, codici ISTAT senza geometrie, audit di qualità, PEC e contatti degli enti, navigazione del portale di un singolo ente).

Il testo applicato differisce da quello testato solo per accenti ripristinati, maiuscole e "portale o geoportale" al posto della barra. Riprova post-applicazione su quattro casi critici (Corine, geoportale Toscana, geoportale Sardegna, query colloquiale positiva): 4/4 con margine pieno. Misure complete in skills/rndt-explorer/evals/trigger-results.json.

## Limiti

- Il giudice è il modello di sessione: un altro modello o harness può triggherare diversamente.
- Le nove skill concorrenti sono un sottoinsieme della lista reale: un concorrente mancante può solo aumentare i falsi positivi misurati, non ridurli.
- Tre run per query: la soglia di 2 su 3 smorza il rumore occasionale ma non misura la varianza oltre k=3.

## Come rilanciare

1. Aggiornare o estendere skills/rndt-explorer/evals/trigger-evals.json.
2. Usare il protocollo in skills/rndt-explorer/evals/trigger-judge-prompt.txt: 3 chiamate per query al modello di sessione con schema JSON {skills, reason}.
3. Contare come trigger se rndt-explorer compare in almeno 2 run su 3, e confrontare con should_trigger.
