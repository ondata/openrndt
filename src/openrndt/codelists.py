"""Codelist statiche RNDT/ISO 19115.

Tutto ciò che è enumerabile lato API e non richiede chiamate di rete.
Permette al comando `discover` di funzionare offline.
"""

from __future__ import annotations

# ISO 19115 — TopicCategoryCode (categorie tematiche dataset).
# Fonte: https://standards.iso.org/iso/19115/resources/Codelists/cat/codelists.xml#MD_TopicCategoryCode
DATA_CATEGORIES: dict[str, str] = {
    "farming": "Agricoltura",
    "biota": "Biota — flora e fauna naturali",
    "boundaries": "Confini amministrativi e legali",
    "climatologyMeteorologyAtmosphere": "Climatologia, meteorologia, atmosfera",
    "economy": "Economia",
    "elevation": "Altimetria",
    "environment": "Ambiente",
    "geoscientificInformation": "Informazioni geoscientifiche",
    "health": "Salute",
    "imageryBaseMapsEarthCover": "Cartografia di base, immagini, copertura del suolo",
    "intelligenceMilitary": "Intelligence, difesa",
    "inlandWaters": "Acque interne",
    "location": "Posizione (indirizzi, toponimi)",
    "oceans": "Oceani",
    "planningCadastre": "Pianificazione e catasto",
    "society": "Società",
    "structure": "Strutture (edifici, infrastrutture)",
    "transportation": "Trasporti",
    "utilitiesCommunication": "Utility e comunicazioni",
}

# Valori per il parametro `sort` (vedi ref/rest-api-rndt.md).
#
# IMPORTANTE (verificato live): il meccanismo reale è `campo:asc|desc` su un campo
# Elasticsearch *sortable* (keyword `_s`, data `_dt`, intero `_i`). I valori
# "amichevoli" `dateDescending`/`dateAscending` documentati sulla pagina ufficiale
# NON ordinano (su RNDT restituiscono ordine identico fra loro → ignorati;
# riconfermato 2026-07-17). Il sort su `title` (campo text) in passato dava errore
# "Fielddata is disabled", ma dal 2026-07-17 risulta funzionare: i campi garantiti
# sortable restano `_s`/`_dt`/`_i`. Non esiste un campo data-di-pubblicazione
# ordinabile.
SORT_VALUES: dict[str, str] = {
    "apiso_Modified_dt:desc": "Per data: ultimi metadati modificati per primi (proxy migliore per 'più recenti').",
    "apiso_Modified_dt:asc": "Per data: metadati modificati meno di recente per primi.",
    "sys_modified_dt:desc": "Per data di reindex catalogo (poco utile: valori ravvicinati).",
    "relevance": "⚠️ Ignorato dal server: stesso ordine del no-sort (verificato 2026-08-30).",
    "dateDescending": "⚠️ Documentato ma NON ordina su RNDT (ignorato, identico a dateAscending).",
    "dateAscending": "⚠️ Documentato ma NON ordina su RNDT (ignorato).",
}

# Formati output del parametro `f`.
OUTPUT_FORMATS: dict[str, str] = {
    "json": "JSON (default)",
    "json-source": "JSON sorgente Elasticsearch (_source grezzo)",
    "atom": "Atom Feed",
    "csw": "Catalog Service Web (XML OGC)",
    "rss": "RSS Feed",
    "csv": "Comma Separated Values",
    "kml": "KML",
    "eros": "Formato proprietario",
}

# Parametri principali dell'endpoint /rest/metadata/search.
SEARCH_PARAMS: dict[str, str] = {
    "q": (
        "Testo libero o query Lucene. ⚠️ Fra termini e clausole separati da spazio "
        "l'operatore implicito è OR (verificato 2026-08-30: `catasto siciliana` = "
        "`catasto OR siciliana`): per restringere scrivi AND esplicito. "
        "-termine per escludere, virgolette per frase esatta, wildcard * (zero o più "
        "char) e ? (un char), anche iniziale e anche su campo esplicito (*palerm*, "
        "EnteResponsabile_s:*Siciliana). I campi _s sono case-sensitive, i _txt no. "
        "Esclusione: (suolo -natura). Raggruppamento: (termine1 termine2). "
        "Date: campo_dt:[2024-01-01T00:00:00Z TO *]. Interi: campo_i:[1 TO 10000]. "
        "Vedi `discover --what lucene_fields` per i campi disponibili."
    ),
    "bbox": "Bounding box WGS84 nel formato xmin,ymin,xmax,ymax.",
    "bbox_crs": "Parametro CLI (non API): CRS esplicito della bbox. Supportati EPSG:4326, CRS:84, WGS84.",
    "dataCategory": "Una o più categorie ISO 19115 separate da virgola.",
    "time": "Intervallo temporale della risorsa yyyy-mm-dd/yyyy-mm-dd.",
    "modified": "Intervallo di modifica del record nel catalogo yyyy-mm-dd/yyyy-mm-dd. Diverso da `time`: filtra quando il metadato è stato aggiornato nel RNDT, non la copertura temporale della risorsa.",
    "org": (
        "Parametro CLI (non API): ente responsabile, tradotto in frase Lucene su "
        "apiso_OrganizationName_txt (campo analizzato: case-insensitive, insensibile "
        "all'ordine dei token). Preferirlo alle wildcard su contact_organizations_s, "
        "che sono case-sensitive e prendono anche i record di altri enti che nominano "
        "quel territorio."
    ),
    "org_exact": (
        "Parametro CLI (non API): ente responsabile in forma esatta e case-sensitive, "
        "tradotto in clausola su EnteResponsabile_s. Alternativo a `org`."
    ),
    "updated_from/updated_to": "Parametro CLI (non API): range date yyyy-mm-dd tradotto in clausola Lucene su apiso_Modified_dt.",
    "published_from/published_to": "Parametro CLI (non API): range date yyyy-mm-dd tradotto in clausola Lucene su apiso_PublicationDate_dt.",
    "profile": (
        "Parametro CLI (non API): preset colonne output per table/csv (`default`, `gis`, `qgis`). "
        "Senza `--format` attiva da solo l'output table."
    ),
    "sort": "Ordinamento 'campo:asc|desc' su campo sortable (es. apiso_Modified_dt:desc). ⚠️ 'dateDescending'/'dateAscending' NON ordinano su RNDT. Vedi SORT_VALUES.",
    "start": "Posizione del primo record (1-based, default 1).",
    "num": "Numero massimo di risultati (default 10, max 5000).",
    "f": "Formato output (vedi OUTPUT_FORMATS).",
    "id": "Filtra per ID metadato.",
}


# Campi Elasticsearch/_source interrogabili via sintassi Lucene nel parametro `q`.
# Fonte: ispezione della risposta JSON di qualunque metadato RNDT (`openrndt get <id>`).
#
# Suffissi e wildcard:
#   _txt  campo analizzato (tokenizzato, lowercase): wildcard trailing e leading OK
#         (palerm*, *palerm*), case-insensitive.
#   _s    campo keyword (non analizzato, case-sensitive): wildcard trailing e leading OK
#         (Palerm*, *Siciliana); con la maiuscola sbagliata il risultato è 0.
#   Riverificato su API reale il 2026-08-29/30: il leading wildcard funziona ovunque.
#   _dt   campo data ISO 8601: usare range [2024-01-01T00:00:00Z TO *].
#   _i    campo intero: usare range [1 TO 10000].
#   _b    campo booleano: valori true | false.
LUCENE_FIELDS: dict[str, str] = {
    # Identificazione
    "apiso_Identifier_s": "ID univoco del metadato",
    "apiso_ParentIdentifier_s": "ID della serie padre",
    "apiso_Type_s": "Tipo risorsa: dataset | series | service",
    "fileid": "Alias dell'ID metadato",
    # Testo descrittivo
    "apiso_Title_txt": "Titolo",
    "apiso_Abstract_txt": "Abstract / descrizione",
    "apiso_Subject_txt": "Parole chiave (array)",
    "keywords_s": "Parole chiave (flat)",
    "apiso_Lineage_txt": "Genealogia / provenienza del dato",
    # Organizzazione e contatti
    "apiso_OrganizationName_txt": "Nome ente responsabile (analizzato: la ricerca per frase è case-insensitive). Campo usato da --org.",
    "EnteResponsabile_s": "Ente responsabile (campo RNDT, keyword: confronto esatto e case-sensitive). Campo usato da --org-exact.",
    "PuntoDiContatto_s": "Punto di contatto",
    "PuntoDiContattoEmail_s": "Email punto di contatto",
    "contact_organizations_s": "Organizzazioni di contatto (array)",
    # Classificazione tematica
    "apiso_TopicCategory_s": "Categoria ISO 19115 (es. planningCadastre)",
    "INSPIRETheme_s": "Tema INSPIRE",
    "OpenDataTheme_s": "Tema open data",
    "AmbitoTerritoriale_s": "Ambito: Regionale | Nazionale | Locale (anche Regional/Local in inglese; il campo manca su ~28% dei record)",
    # Date (sortable: usabili sia in range [da TO a] sia come `sort=campo:desc`)
    "apiso_Modified_dt": "dateStamp del metadato (sortable). Miglior proxy per 'ultimi aggiornati'.",
    "apiso_RevisionDate_dt": "Data revisione risorsa = ISO dateType 'revision' (sortable).",
    "apiso_CreationDate_dt": "Data creazione risorsa. Spesso null/fittizia (es. 2012-01-01): inaffidabile per sort.",
    "sys_created_dt": "Data creazione record nel catalogo (reindex).",
    "sys_modified_dt": "Istante di indicizzazione nel catalogo (sortable, ma poco informativa). È il campo top-level `updated` del JSON grezzo dell'API; negli output openrndt si chiama `indexed`.",
    # Accesso e licenze
    "apiso_AccessConstraints_s": "Vincoli di accesso / licenza (es. CC BY 4.0)",
    "apiso_OtherConstraints_s": "Altri vincoli",
    "apiso_Classification_s": "Classificazione (es. unclassified)",
    "isOpendata": "Licenza open data (stringa, es. 'CC BY 4.0'). Usa isOpendata:* per tutti gli open data.",
    # Formato e qualità
    "apiso_Format_s": "Formati disponibili (es. GML, Shapefile, GeoTIFF)",
    "apiso_Denominator_i": "Denominatore scala (intero, usare range [min TO max])",
    "apiso_CRS": "Sistema di riferimento (es. EPSG:4326)",
    "apiso_Degree_b": "Conformità INSPIRE: true | false",
}


def codelist_payload() -> dict[str, dict[str, str]]:
    """Payload completo restituito da `openrndt discover --format json`."""
    return {
        "data_categories": DATA_CATEGORIES,
        "sort_values": SORT_VALUES,
        "output_formats": OUTPUT_FORMATS,
        "search_params": SEARCH_PARAMS,
        "lucene_fields": LUCENE_FIELDS,
    }
