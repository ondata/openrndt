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

# Valori validi per il parametro `sort` (vedi ref/rest-api-rndt.md).
SORT_VALUES: dict[str, str] = {
    "dateDescending": "Data decrescente (default)",
    "dateAscending": "Data crescente",
    "relevance": "Pertinenza",
    "title": "Titolo (crescente)",
    "title:desc": "Titolo (decrescente)",
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
        "Testo libero o query Lucene: AND implicito, -termine per escludere, "
        "virgolette per frase esatta, wildcard * (zero o più char) e ? (un char). "
        "Testo libero: wildcard ovunque (*suo*, na??ra). "
        "Su campo specifico (campo:valore): solo trailing (palerm*); "
        "leading wildcard (*palerm*) non supportato su campo esplicito. "
        "Esclusione: (suolo -natura). Raggruppamento: (termine1 termine2). "
        "Date: campo_dt:[2024-01-01T00:00:00Z TO *]. Interi: campo_i:[1 TO 10000]. "
        "Vedi `discover --what lucene_fields` per i campi disponibili."
    ),
    "bbox": "Bounding box WGS84 nel formato xmin,ymin,xmax,ymax.",
    "dataCategory": "Una o più categorie ISO 19115 separate da virgola.",
    "time": "Intervallo temporale della risorsa yyyy-mm-dd/yyyy-mm-dd.",
    "modified": "Intervallo di modifica del record nel catalogo yyyy-mm-dd/yyyy-mm-dd. Diverso da `time`: filtra quando il metadato è stato aggiornato nel RNDT, non la copertura temporale della risorsa.",
    "sort": "Ordinamento (vedi SORT_VALUES). Default: dateDescending.",
    "start": "Posizione del primo record (1-based, default 1).",
    "num": "Numero massimo di risultati (default 10, max 5000).",
    "f": "Formato output (vedi OUTPUT_FORMATS).",
    "id": "Filtra per ID metadato.",
}


# Campi Elasticsearch/_source interrogabili via sintassi Lucene nel parametro `q`.
# Fonte: ispezione della risposta JSON di qualunque metadato RNDT (`openrndt get <id>`).
#
# Suffissi e wildcard:
#   _txt  campo analizzato (tokenizzato, lowercase): wildcard trailing OK (palerm*),
#         leading wildcard (*palerm*) NON supportato.
#   _s    campo keyword (non analizzato, case-sensitive): wildcard solo trailing (Palerm*),
#         leading wildcard (*Palerm*) bloccato da Elasticsearch.
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
    "apiso_OrganizationName_txt": "Nome ente responsabile",
    "EnteResponsabile_s": "Ente responsabile (campo RNDT)",
    "PuntoDiContatto_s": "Punto di contatto",
    "PuntoDiContattoEmail_s": "Email punto di contatto",
    "contact_organizations_s": "Organizzazioni di contatto (array)",
    # Classificazione tematica
    "apiso_TopicCategory_s": "Categoria ISO 19115 (es. planningCadastre)",
    "INSPIRETheme_s": "Tema INSPIRE",
    "OpenDataTheme_s": "Tema open data",
    "AmbitoTerritoriale_s": "Ambito: Nazionale | Regionale | Provinciale | Comunale",
    # Date
    "apiso_Modified_dt": "Data modifica metadato (ISO 8601, usare range [da TO a])",
    "apiso_RevisionDate_dt": "Data revisione risorsa (ISO 8601, usare range [da TO a])",
    "sys_created_dt": "Data creazione nel catalogo",
    "sys_modified_dt": "Data ultima modifica nel catalogo",
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
