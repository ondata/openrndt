# Vedere i risultati nel browser: i link a GeoLibre web

La CLI produce indirizzi che aprono [GeoLibre web](https://web.geolibre.app) con il plugin [openrndt-geolibre](https://github.com/ondata/openrndt-geolibre): chi li apre vede la scheda, il layer o l'intera ricerca su una mappa, senza installare nulla. Proponili quando l'utente vuole guardare i dati e non costruire una mappa da consegnare. Per un progetto `.geolibre`, una pagina `export_html` o una mappa dei footprint costruita con il server MCP di GeoLibre la guida è [`geolibre.md`](./geolibre.md).

## I tre link

| Cosa apre | Come si ottiene | CLI | Plugin nel registro |
|---|---|---|---|
| la scheda nel pannello, con i servizi WMS/WFS pronti da aggiungere | `geolibre_url` in `search` (JSON, `compact`, `csv`, profili `gis`/`qgis`), `get` e nelle proprietà di `footprints`; non in `--format table` | dalla 3.5.0 | qualunque |
| la scheda con un layer WMS già sulla mappa | `resources <id> --layers`: un `geolibre_url` per layer in `layers[]` | dalla 3.6.0 | dalla 0.3.5; dalla 0.3.8 la mappa si apre sui layer |
| la stessa ricerca di `search`, con i footprint sulla mappa | `search … --geolibre-link` stampa solo l'indirizzo; con `--format json` l'oggetto `geolibre_search` (`url`, `untranslated`, `notes`) sta accanto a `total` | dalla 3.8.0; `--ipa` e enti con la virgola dalla 3.10.0 | dalla 0.3.8; `rndtIpa` dalla 0.3.11 |

Per sapere se la CLI installata ha il terzo: `openrndt search --help | grep geolibre-link`.

```bash
openrndt search --q fiumi --bbox 9,45,10,46 --published-from 2020-01-01 --geolibre-link
# https://web.geolibre.app/?plugin=openrndt-geolibre&rndt=fiumi&rndtBbox=9,45,10,46&rndtDate=publication&rndtFrom=2020-01-01

openrndt resources r_emiro:2022-03-11T113115 --layers | jq -r '.layers[] | "\(.name)\t\(.geolibre_url)"'
```

Un `geolibre_url` di layer `null` ha una `note` che dice perché: nessun CRS che GeoLibre disegna, o nome già in un altro servizio della scheda.

## Come si traduce la ricerca

Il link porta i filtri che il plugin ha. Gli altri il link li ignora e la CLI li elenca su stderr («Non applicati nel link»), insieme alle differenze da sapere («Nota sul link»).

| CLI | Nel link | Note |
|---|---|---|
| `--q` | `rndt` | stesse regole in `all`/`any`; una `q` con sintassi Lucene va con `rndtMode=lucene` |
| `--q-mode any`/`lucene` | `rndtMode` | |
| `--bbox` | `rndtBbox` | |
| `--org`, `--org-exact` | `rndtOrg` | nel plugin è sempre «contiene»: `--org-exact` può trovare anche varianti del nome; un nome con una virgola va tra virgolette doppie, dal plugin 0.3.9 |
| `--data-category` | `rndtKeywords` | |
| `--updated-from/to` | `rndtDate=modified`, `rndtFrom`/`rndtTo` | |
| `--published-from/to` | `rndtDate=publication`, `rndtFrom`/`rndtTo` | un solo intervallo: con `--updated-*` le date di pubblicazione restano fuori |
| `--sort` | `rndtSort` | solo `title:asc`/`desc` e `apiso_Modified_dt:desc`/`asc` |
| `--id` | `rndt=<id>` | apre quella scheda, gli altri filtri non contano |
| `--ipa` | `rndtIpa` | più codici separati da virgola, maiuscole indifferenti; dal plugin 0.3.11 |
| `--time`, `--modified` | nessuno | elencati su stderr |
| `--start`, `--num` | nessuno | il link apre la prima pagina |

Senza `--bbox` il link porta `rndtView`, il riquadro dei risultati della pagina: la mappa si apre sull'area dei dati senza filtrarli.

Verificato il 2026-10-10 su cinque ricerche (testo in AND, riquadro con date di pubblicazione, ente con categoria, Lucene, testo in `any` con data della scheda e ordinamento): stesso numero di schede nella CLI e nel pannello aperto dal link, con il plugin 0.3.8. Il 2026-10-10, con il plugin 0.3.12, anche `--ipa r_sardeg` (766) e Arpae per esteso, il nome con la virgola (383).

## Limiti

- **Solo GeoLibre web.** Non GeoLibre Desktop, che non apre i link web, né `layout=viewer`, dove i plugin del registro non si aprono da link (opengeos/GeoLibre#2898).
- **La prima volta** chi apre il link deve accettare il plugin («Trust and load»).
- **Versione del plugin.** Conta quella del registro di GeoLibre, che il link installa. Con una precedente a quelle della tabella il link si apre ma non fa tutto: prima della 0.3.5 il layer non va sulla mappa, dalla 0.3.5 alla 0.3.7 il layer entra ma la mappa resta dov'è (AGEA con la 0.3.7: zoom 4.3 su mezza Europa), prima della 0.3.8 `rndtDate=modified` non è un valore valido e l'intervallo di date finisce sulla data predefinita del plugin, la revisione; prima della 0.3.9 un ente tra virgolette dà 0 schede; prima della 0.3.11 `rndtIpa` è ignorato. Nel registro dal 2026-10-10 c'è la 0.3.12.
- **I dati li scarica il browser di chi apre.** Un servizio solo `http://` può non vedersi su una pagina https; un WMS senza CORS non si legge, e probabilmente nemmeno uno che manda due intestazioni `Access-Control-Allow-Origin`: l'ArcGIS ISPRA, che le manda, dava `Failed to fetch (0)` in una pagina MapLibre (prova del 30 agosto 2026), ma in GeoLibre web la causa non è isolata, perché lì il servizio era dichiarato anche `http://`; un servizio lento resta lento. Lo stesso link può funzionare per un servizio e non per un altro della stessa scheda.
- **La ricerca è dal vivo.** Il link riapre la ricerca, non i risultati di oggi: se il catalogo cambia, cambiano anche le schede. Per una consegna che resta uguale serve un progetto (vedi [`geolibre.md`](./geolibre.md)).
- **Solo la prima pagina**, e senza i filtri che il plugin non ha: dillo all'utente quando la CLI li elenca su stderr.
- **`rndtView` e le schede nazionali.** Se nella pagina c'è una scheda con riquadro nazionale, la mappa si apre sull'Italia intera.
- **Lunghezza.** Un link con molti layer supera i 2.000 caratteri, la soglia oltre cui alcune app di posta e chat lo tagliano (circa 15 layer).
