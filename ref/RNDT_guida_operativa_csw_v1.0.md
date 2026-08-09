![](image_p1_2.png)

![](image_p1_0.png)

![](image_p1_1.png)

#### Agenzia per l'Italia Digitale

~

# MANUALE RNDT

## 6. Guida operativa all'uso del servizio di ricerca (CSW) in coerenza con le regole tecniche di INSPIRE

-----



-----

**INDICE**

**PREMESSA ........................................................................................................................................ 5 1 IL SERVIZIO DI RICERCA DEL RNDT ............................................................................... 7**

1.1 Caratteristiche generali.......................................................................................................... 7 1.2 Punti di connessione del servizio .......................................................................................... 8 1.3 Le operazioni del servizio ..................................................................................................... 9 1.4 Requisiti sulla lingua ........................................................................................................... 11

**2 ESEMPI DI RICHIESTE ........................................................................................................ 12**

2.1 Richiesta di GetCapabilities ................................................................................................ 12 2.2 Richiesta di GetRecords ...................................................................................................... 12 2.3 Richiesta di GetRecordById................................................................................................ 14 2.4 Richiesta di DescribeRecord ............................................................................................... 15

**ALLEGATO A - CRITERI DI RICERCA / ELEMENTI INTERROGABILI (QUERYABLES) ............................................................................................................................. 17**

©

**INFORMAZIONI Agenzia per l'Italia Digitale**

Viale Marx, 43 - 00137 ROMA e-mail: info@rndt.gov.it

-----



-----

#### PREMESSA

Il D. Lgs. n. 32/20101 , norma di recepimento della Direttiva INSPIRE2 in Italia, individua il Repertorio Nazionale dei Dati Territoriali (RNDT) come catalogo nazionale dei metadati riguardanti i dati territoriali ed i servizi ad essi relativi, disponibili presso le pubbliche amministrazioni. In virtù di ciò, il DM 10 novembre 20113 stabilisce che, nell'ambito dell'infrastruttura nazionale per l'informazione territoriale e il monitoraggio ambientale di cui è parte integrante, il RNDT eroga il servizio di ricerca (discovery service) di cui all'art. 7 comma 1 lettera a) del citato D. Lgs n. 32/2010. Il Regolamento (CE) 976/2009, recante attuazione della direttiva INSPIRE per quanto riguarda i servizi di rete, stabilisce i requisiti per l'istituzione e l'aggiornamento di detti servizi e indica le disposizioni relative alla qualità degli stessi. Inoltre, per quanto riguarda i servizi di ricerca in particolare, fornisce (cfr. allegato II) i requisiti e le caratteristiche specifiche. Oltre al Regolamento sopra citato, per i servizi di ricerca è stata prodotta da INSPIRE un'apposita guida tecnica4 (identificata nel seguito con [INS DSTG]), che descrive, in modo dettagliato, gli aspetti relativi all'implementazione e alle relazioni con gli Standard, le tecnologie e le pratiche esistenti. In particolare, relativamente agli Standard di riferimento, la guida stabilisce che i requisiti e le raccomandazioni fornite sono basate sulle specifiche dell'Open Geospatial Consortium - OGC5 (identificate nel seguito con [CSW ISO AP]), di cui la guida medesima rappresenta un profilo per la comunità di INSPIRE. Il servizio di ricerca implementato per il RNDT è conforme ai requisiti e alle raccomandazioni specificati dalla guida tecnica INSPIRE [INS DSTG] e alle indicazioni definite dalle citate specifiche OGC [CSW ISO AP], in conformità ai requisiti di implementazione (implementation *requirements) 1 e 2 di cui a [INS DSTG].* Il presente documento illustra le caratteristiche del servizio e fornisce tutte le indicazioni utili per il suo più efficace utilizzo.

1 DECRETO LEGISLATIVO 27 gennaio 2010 , n. 32 recante "Attuazione della direttiva 2007/2/CE, che istituisce *un'infrastruttura per l'informazione territoriale nella Comunità europea (INSPIRE)".* 2 DIRETTIVA 2007/2/CE DEL PARLAMENTO EUROPEO E DEL CONSIGLIO del 14 marzo 2007 che istituisce un'Infrastruttura per l'informazione territoriale nella Comunità europea (Inspire). 3 Decreto 10 novembre 2011 del Ministro per la Pubblica Amministrazione e l'Innovazione di concerto con il Ministro dell'Ambiente e della Tutela del Territorio e del Mare recante "Regole tecniche per la definizione del contenuto del *Repertorio nazionale dei dati territoriali, nonché delle modalità di prima costituzione e di aggiornamento dello stesso",* pubblicato sulla G.U. serie generale n. 48 del 27 febbraio 2012, supplemento ordinario n. 37. 4 *Technical Guidance for the implementation of INSPIRE Discovery Services, v. 3.1 del 07/11/2011*

5 OGC Catalogue Services Specification 2.0.2 - ISO Metadata Application Profile for CSW 2.0

-----

Per quanto non specificato nel presente documento si rimanda alle specifiche OGC [CSW ISO AP] e alla guida tecnica INSPIRE [INS DSTG] di cui sopra.

-----

#### 1 IL SERVIZIO DI RICERCA DEL RNDT

### 1.1 Caratteristiche generali

La Direttiva INSPIRE, all'art. 11 (recepito con l'art. 7 del D. Lgs. 32/2010), identifica i servizi per i set di dati territoriali che le autorità pubbliche devono istituire e gestire. Tra questi, ci sono anche i servizi di ricerca (discovery services) definiti come i servizi che consentono "di cercare i set di dati territoriali e i servizi ad essi relativi in base al contenuto dei *metadati corrispondenti e di visualizzare il contenuto dei metadati".* L'implementazione di tali servizi è basata sulle Specifiche OGC sui CSW [CSW ISO AP] e sulla Guida Tecnica INSPIRE [INS DSTG]. Il profilo INSPIRE delle Specifiche OGC, rappresentato in tale ultimo documento, definisce l'implementazione delle seguenti operazioni:

- **Get Discovery Service Metadata - Operazione che fornisce tutte le informazioni** necessarie sul servizio di discovery e descrive le capabilities del servizio;
- **Discover Metadata - Operazione che consente di interrogare i metadati da un servizio di**

ricerca;

- **Publish Metadata - Operazione che consente di inserire, aggiornare e cancellare i metadati** nel servizio di discovery attraverso meccanismi push e/o pull;
- **Link Discovery Service - Operazione che consente di dichiarare la disponibilità di più** servizi di ricerca distribuiti fruibili attraverso il servizio di ricerca dello Stato Membro pur mantenendo i metadati delle risorse a livello dell'Amministrazione competente. Nella tabella 1 viene rappresentata la corrispondenza tra le operazioni previste da INSPIRE [INS

**DSTG] e quelle previste dalle Specifiche OGC [CSW ISO AP]. Nella medesima tabella, in**

grassetto, sono indicate le operazioni implementate nel RNDT. Per ogni operazione è indicata, tra parentesi, la relativa cardinalità: O sta per obbligatorio, C per condizionato, Op per opzionale. Come si evince dalla tabella, alcune operazioni previste da OGC non sono richieste da INSPIRE; tuttavia, il servizio di ricerca del RNDT implementa tutte le operazioni indicate come "mandatory" nelle specifiche OGC.

-----

| Operazioni INSPIRE |  |
|---|---|
| Get Discovery Service Metadata (O) |  |
| Discover Metadata (O) |  |
| Publish Metadata (C) |  |
| Link Discovery service (O) |  |
| Non previsto |  |
| Non previsto |  |
| Non previsto |  |

**Tab. 1 - Mapping operazioni INSPIRE - operazioni OGC**

#### Operazioni OGC CSW ISO AP OGC_Service.GetCapabilities (O) CSW Discovery.GetRecords (O)

CSWT Manager.Transaction or

#### CSWT Manager.Harvest (C)

Combinazione di OGC\_Service.GetCapabilities e CSW Discovery.GetRecords oppure CSWT Manager.Transaction or CSWT Manager.Harvest.

#### CSW Discovery.GetRecordById (O) CSW Discovery.DescribeRecord (O)

CSW Discovery.GetDomain (Op)

Le Specifiche OGC [CSW ISO AP] fanno distinzione tra due tipi di servizi di catalogo: un servizio "read-only" (indicato nella tabella con l'acronimo CSW) e uno transazionale (indicato nella tabella con l'acronimo CSWT). La presente guida è relativa solo alle operazioni del servizio CSW (read*only).*

Nella tabella 2 sono illustrati, invece, per ciascuna operazione, i metodi di codifica (encoding) applicati nel servizio del RNDT.

| Operazioni CSW |  |
|---|---|
| GetCapabilities |  |
| GetRecords |  |
| GetRecordById |  |
| DescribeRecord |  |
| Harvest |  |

**Tab. 2 - Metodi di codifica delle operazioni implementate nel servizio del RNDT**

#### Encoding della richiesta

XML (POST + SOAP) e KVP6 (GET) XML (POST + SOAP) XML (POST + SOAP) e KVP (GET) XML (POST + SOAP) XML (POST + SOAP)

### 1.2 Punti di connessione del servizio

Come rappresentato nel documento di GetCapabilities, i punti di connessione attraverso cui si può accedere alle operazioni del servizio di ricerca del RNDT sono i seguenti:

6 Coppia chiave-valore (Keyword-Value Pairs); codifica utilizzata per il passaggio di parametri tramite URL nelle richieste HTTP/GET

-----

- per le richieste effettuate in HTTP/GET e HTTP/POST-SOAP:

http://www.rndt.gov.it/RNDT/CSW;

- per le richieste effettuate in HTTP/POST - XML:

**http://www.rndt.gov.it/RNDT/CSW/POST.**

### 1.3 Le operazioni del servizio

Nei successivi paragrafi vengono illustrate le caratteristiche delle operazioni implementate nel servizio di ricerca del RNDT, specificando, in parentesi quadre [...], i requisiti della guida tecnica INSPIRE [INS DSTG] soddisfatti nell'implementazione. Nel capitolo 2, per le varie operazioni, vengono riportati gli esempi di richiesta nei vari metodi di codifica implementati.

#### 1.3.1 Operazione di GetCapabilities

L'operazione GetCapabilities (Get Discovery Service Metadata per INSPIRE) consente di recuperare i metadati del servizio da un server. L'operazione implementata nel RNDT contiene le estensioni introdotte da INSPIRE rispetto alle specifiche OGC; in particolare:

- nel file XML di risposta sono contenuti gli elementi introdotti da [INS DSTG] non previsti dalle Specifiche OGC ed è stato indicato l'URL del set di metadati che descrivono il servizio di ricerca conformemente alle regole tecniche RNDT e alle indicazioni INSPIRE [INS

#### DSTG - implementation requirement 7 e 8];

- nella risposta è stata altresì aggiunta la sezione "Extended Capabilities", introdotta da [INS

**DSTG], in cui è indicata la lingua di risposta del servizio (lingua di default ed eventuali**

altre lingue supportate) [INS DSTG - implementation requirements 7, 27, 28 e 29]

- nella richiesta in HTTP/GET è possibile specificare il parametro aggiuntivo introdotto da [INS DSTG], "language" [INS DSTG - implementation requirements 6, 25 e 26]. A tale proposito, v. esempio di richiesta in HTTP/GET al § 2.1.1.

#### 1.3.2 Operazione di GetRecords

L'operazione GetRecords (Discover Metadata per INSPIRE) consente di richiedere, ad un servizio di ricerca, i metadati di dati e servizi, con la possibilità di definire dei criteri per 'filtrare' gli stessi metadati in base la loro contenuto. I parametri supportati nell'operazione sono conformi alle estensioni introdotte in [INS DSTG -

**Implementation Requirements 9, 10 e 11].**

-----

I criteri di ricerca (queryables) supportati dal servizio del RNDT sono quelli richiesti da [INS

**DSTG] e indicati nel documento di GetCapabilities [INS DSTG - Implementation Requirements 4, 5, 18, 19, 20, 21 e 22].**

In relazione a ciò, come indicato nelle specifiche OGC [CSW ISO AP], ogni elemento interrogabile deve essere espresso, nella richiesta di GetRecords, attraverso un nome qualificato preceduto dal prefisso "apiso" che rappresenta il namespace *http://www.opengis.net/cat/csw/apiso/1.0. A tale proposito, nell'allegato A sono riportati gli* elementi interrogabili nel formato innanzi indicato. Conformemente a quanto previsto dal [INS DSTG], i parametri delle richieste al servizio del RNDT devono essere impostati nel modo seguente [INS DSTG - Implementation

#### Recommendation 2]:

- resultType="results";
- outputFormat="application/xml";
- outputSchema="http://www.isotc211.org/2005/gmd";
- ElementSetName="full". Inoltre, siccome l'attuale versione del servizio CSW del RNDT non contempla il profilo dei metadati di cui allo Standard Dublin Core (espresso attraverso l'elemento csw:Record), il parametro *typeName deve essere impostato nel modo seguente:*
- typeName="gmd:MD\_Metadata". Nel documento di GetCapabilities sono anche indicati gli operatori spaziali e di confronto utilizzabili per definire i criteri di ricerca all'interno di una richiesta. Nella risposta a una richiesta di GetRecords, vengono riportati tutti i record che soddisfano i criteri di ricerca impostati, contenenti tutti i metadati previsti dal RNDT e, di conseguenza, dal Regolamento INSPIRE n. 1205/2008 [INS DSTG - Implementation Requirement 12].

#### 1.3.3 Operazione di GetRecordById

L'operazione di GetRecordById consente di recuperare uno o più record specifici in base ai loro identificatori (coincidenti con l'elemento "fileIdentifier" dello Standard ISO TS 19139). L'operazione non è richiesta da [INS DSTG]. Stante ciò, per i parametri della richiesta comuni vale quanto indicato per l'operazione GetRecords al paragrafo precedente. Nella risposta viene riportato il/i record relativo/i allo/agli identificatore/i indicati nella richiesta.

-----

#### 1.3.4 Operazione di DescribeRecord

L'operazione di DescribeRecord, non richiesta da [INS DSTG], consente ad un client di scoprire gli elementi del modello di dati supportato dal servizio di catalogo. Anche in questo caso, il parametro della richiesta typeName deve essere impostato col valore "gmd:MD\_Metadata".

**1.3.5** | Operazione di Link Discovery Service

L'operazione consente di scoprire le risorse informative di un servizio di ricerca, conforme al Regolamento (CE) n. 976/2009, attraverso il servizio di ricerca dello Stato Membro (nel caso in parola, il servizio del RNDT). L'implementazione di tale operazione può avvenire, secondo [INS

**DSTG], in base a tre scenari: centralizzato, approccio client e ricerca federata.**

L'approccio seguito dal RNDT è certamente quello centralizzato, considerato che il DM relativo alle regole tecniche del RNDT sancisce l'obbligo, per le pubbliche amministrazioni, di inserire nel RNDT i metadati riguardanti i dati territoriali e i servizi ad essi relativi. L'operazione di Link Discovery Service come richiesto da [INS DSTG], pertanto, è implicitamente coerente con le indicazioni della guida tecnica [INS DSTG - Implementation Requirement 14] . Stante ciò, siccome il servizio del RNDT ha implementato anche l'operazione di harvesting (attualmente in fase di test), per le pubbliche amministrazioni che dispongono, a loro volta, di servizi di catalogo conformi a [INS DSTG], sarà possibile trasmettere i propri metadati attraverso il meccanismo di pull proprio dell'operazione di harvesting [INS DSTG - Implementation

**Requirement 15].**

In conseguenza di ciò, il documento di GetCapabilities sarà aggiornato secondo quanto previsto da [INS DSTG].

### 1.4 Requisiti sulla lingua

Sebbene la versione attuale del RNDT non gestisca gli aspetti del multilinguismo, il servizio di ricerca segue i principi di base indicati da [INS DSTG]. In particolare, oltre a quanto indicato nei paragrafi precedenti, le operazioni del servizio sono coerenti con i requisiti espressi in [INS DSTG

**- Implementation Requirements 23, 24, 30, 31 e 32].**

-----

#### 2 ESEMPI DI RICHIESTE

Nel presente capitolo vengono riportati alcuni esempi di richieste per le varie operazioni implementate nel servizio di ricerca del RNDT.

### 2.1 Richiesta di GetCapabilities

La richiesta di GetCapabilities può essere effettuata sia in HTTP/GET che in HTTP/POST (XML o SOAP).

#### 2.1.1 GetCapabilities in HTTP/GET

http://www.rndt.gov.it/RNDT/CSW?request=GetCapabilities&service=CSW&acceptFormats=application%2Fxml&LA NGUAGE=ita

#### 2.1.2 GetCapabilities in HTTP/POST - XML

<?xml version="1.0" encoding="UTF-8"?> <GetCapabilities service="CSW" xmlns="http://www.opengis.net/cat/csw/2.0.2" xmlns:ogc="http://www.opengis.net/ogc" xmlns:ows="http://www.opengis.net/ows" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/cat/csw/2.0.2 http://schemas.opengis.net/csw/2.0.2/CSW-discovery.xsd">

<ows:AcceptVersions>

<ows:Version>2.0.2</ows:Version> </ows:AcceptVersions> </GetCapabilities>

#### 2.1.3 GetCapabilities in HTTP/POST - SOAP

<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:ows="http://www.opengis.net/ows">

<soapenv:Header/> <soapenv:Body>

<csw:GetCapabilities xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:ows="http://www.opengis.net/ows" service="CSW">

<ows:AcceptVersions>

<ows:Version>2.0.2</ows:Version> </ows:AcceptVersions> <ows:AcceptFormats>

<ows:OutputFormat>application/xml</ows:OutputFormat> </ows:AcceptFormats> </csw:GetCapabilities> </soapenv:Body> </soapenv:Envelope>

### 2.2 Richiesta di GetRecords

I criteri di ricerca e gli operatori spaziali e di confronto utilizzabili nelle richieste di GetRecords sono indicati nel documento di GetCapabilities. Negli esempi che seguono si utilizzano solo alcuni

-----

di essi. Per maggiori dettagli sulla corrispondenza tra i parametri specificati nei criteri di ricerca (queryables) e i corrispondenti metadati si vedano l'allegato A del presente documento e le guide operative per la compilazione dei metadati RNDT sui dati e sui servizi7 . Tramite le richieste relative agli esempi 2.2.1 e 2.2.3 vengono ricercati dati e servizi per cui il metadato corripondente all'identificatore del file inizia per 'r\_ligur'. Tramite le richiesta relativa all'esempio 2.2.2 vengono invece ricercati i soli servizi (metadato corripondente al Livello gerarchico uguale a 'service') per cui il metadato corripondente all'identificatore del file inizia per 'p\_tp'.

#### 2.2.1 Esempio 1 di GetRecords in HTTP/POST - XML

<?xml version="1.0" encoding="UTF-8"?> <csw:GetRecords service="CSW" version="2.0.2" outputFormat="application/xml" outputSchema="http://www.isotc211.org/2005/gmd" resultType="results" xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:ogc="http://www.opengis.net/ogc" xmlns:apiso="http://www.opengis.net/cat/csw/apiso/1.0" xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/cat/csw/2.0.2 http://schemas.opengis.net/csw/2.0.2/CSW-discovery.xsd">

<csw:Query typeNames="gmd:MD\_Metadata">

<csw:ElementSetName>full</csw:ElementSetName> <csw:Constraint version="1.1.0">

<ogc:Filter>

<ogc:PropertyIsLike wildCard="%" singleChar="\_" escapeChar="/">

<ogc:PropertyName>apiso:identifier</ogc:PropertyName> <ogc:Literal>r\_ligur%</ogc:Literal> </ogc:PropertyIsLike> </ogc:Filter> </csw:Constraint> </csw:Query> </csw:GetRecords>

#### 2.2.2 Esempio 2 di GetRecords in HTTP/POST - XML

<?xml version="1.0" encoding="UTF-8"?> <csw:GetRecords service="CSW" version="2.0.2" outputFormat="application/xml" outputSchema="http://www.isotc211.org/2005/gmd" resultType="results" xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:ogc="http://www.opengis.net/ogc" xmlns:apiso="http://www.opengis.net/cat/csw/apiso/1.0" xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/cat/csw/2.0.2 http://schemas.opengis.net/csw/2.0.2/CSW-discovery.xsd">

<csw:Query typeNames="gmd:MD\_Metadata">

<csw:ElementSetName>full</csw:ElementSetName> <csw:Constraint version="1.1.0">

<ogc:Filter>

<ogc:And>

<ogc:PropertyIsLike wildCard="%" singleChar="\_" escapeChar="/">

<ogc:PropertyName>apiso:identifier</ogc:PropertyName> <ogc:Literal>p\_tp%</ogc:Literal> </ogc:PropertyIsLike>

-----

<ogc:PropertyIsEqualTo>

<ogc:PropertyName>apiso:type</ogc:PropertyName> <ogc:Literal>service</ogc:Literal> </ogc:PropertyIsEqualTo> </ogc:And> </ogc:Filter> </csw:Constraint> </csw:Query> </csw:GetRecords>

#### 2.2.3 GetRecords in HTTP/POST - SOAP

<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:ows="http://www.opengis.net/ows">

<soapenv:Header/> <soapenv:Body>

<csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:apiso="http://www.opengis.net/cat/csw/apiso/1.0" xmlns:ogc="http://www.opengis.net/ogc" xmlns:gmd="http://www.isotc211.org/2005/gmd" service="CSW" version="2.0.2" resultType="results" outputFormat="application/xml" outputSchema="http://www.isotc211.org/2005/gmd" startPosition="1" maxRecords="20">

<csw:Query typeNames="gmd:MD\_Metadata">

<csw:ElementSetName typeNames="gmd:MD\_Metadata">full</csw:ElementSetName>

<csw:Constraint version="1.1.0">

<ogc:Filter>

<ogc:PropertyIsLike wildCard="%" singleChar="\_" escapeChar="/">

<ogc:PropertyName>apiso:identifier</ogc:PropertyName> <ogc:Literal>r\_ligur%</ogc:Literal> </ogc:PropertyIsLike> </ogc:Filter> </csw:Constraint> </csw:Query> </csw:GetRecords> </soapenv:Body> </soapenv:Envelope>

### 2.3 Richiesta di GetRecordById

Le richieste di GetRecordById possono essere effettuate sia in HTTP/GET che in HTTP/POST (XML e SOAP). Tramite le richieste di cui agli esempi 2.3.1, 2.3.3 e 2.3.5, vengono ricercati i metadati relativi a un singolo dato/servizio. Tramite le richieste di cui agli esempi 2.3.2 e 2.3.4 vengono ricercati invece i metadati relativi a tre differenti dati/servizi.

#### 2.3.1 Esempio 1 di GetRecordById in HTTP/GET

http://www.rndt.gov.it/RNDT/CSW?request=GetRecordById&service=CSW&version=2.0.2&id=agid:000001:2013020 4:100158&ELEMENTSETNAME=full&OUTPUTSCHEMA=http://www.isotc211.org/2005/gmd

#### 2.3.2 Esempio 2 di GetRecordById in HTTP/GET

4:100158,r\_abruzz:00147:20120710:111934,abfa:00002:20120626:073614&ELEMENTSETNAME=full&OUTPUTS CHEMA=http://www.isotc211.org/2005/gmd

-----

#### 2.3.3 Esempio 1 di GetRecordById in HTTP/POST - XML

<?xml version="1.0" encoding="UTF-8"?> <csw:GetRecordById service="CSW" version="2.0.2" outputFormat="application/xml" outputSchema="http://www.isotc211.org/2005/gmd" xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/cat/csw/2.0.2 http://schemas.opengis.net/csw/2.0.2/CSW-discovery.xsd">

<csw:Id>agid:000001:20130204:100158</csw:Id> <csw:ElementSetName>full</csw:ElementSetName> </csw:GetRecordById>

#### 2.3.4 Esempio 2 di GetRecordById in HTTP/POST - XML

<?xml version="1.0" encoding="UTF-8"?> <csw:GetRecordById service="CSW" version="2.0.2" outputFormat="application/xml" outputSchema="http://www.isotc211.org/2005/gmd" xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/cat/csw/2.0.2 http://schemas.opengis.net/csw/2.0.2/CSW-discovery.xsd">

<csw:Id>agid:000001:20130204:100158,r\_abruzz:00147:20120710:111934</csw:Id> <csw:Id>abfa:00002:20120626:073614</csw:Id> <csw:ElementSetName>full</csw:ElementSetName> </csw:GetRecordById>

#### 2.3.5 Esempio 1 di GetRecordById in HTTP/POST - SOAP

<soapenv:Envelope xmlcsw:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlcsw:csw="http://www.opengis.net/cat/csw/2.0.2" xmlcsw:ows="http://www.opengis.net/ows">

<soapenv:Header/> <soapenv:Body>

<csw:GetRecordById service="CSW" version="2.0.2" outputFormat="application/xml" outputSchema="http://www.isotc211.org/2005/gmd">

<csw:Id>agid:000001:20130204:100158</csw:Id> <csw:ElementSetName>full</csw:ElementSetName> </csw:GetRecordById> </soapenv:Body> </soapenv:Envelope>

### 2.4 Richiesta di DescribeRecord

#### 2.4.1 DescribeRecord in HTTP/POST - XML

<?xml version="1.0" encoding="UTF-8"?> <DescribeRecord service="CSW" version="2.0.2" xmlns="http://www.opengis.net/cat/csw/2.0.2" xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/cat/csw/2.0.2 http://schemas.opengis.net/csw/2.0.2/CSW-discovery.xsd">

<TypeName>gmd:MD\_Metadata</TypeName> </DescribeRecord>

#### 2.4.2 DescribeRecord in HTTP/POST - SOAP

<soapenv:Header/>

-----

<soapenv:Body>

<csw:DescribeRecord service="CSW" version="2.0.2" outputFormat="application/xml" schemaLanguage="http://www.w3.org/XML/Schema" xmlns:gmd="http://www.isotc211.org/2005/gmd">

<csw:TypeName>gmd:MD\_Metadata</csw:TypeName> </csw:DescribeRecord> </soapenv:Body> </soapenv:Envelope>

-----

#### ALLEGATO A - Criteri di ricerca / Elementi interrogabili (queryables)

Nella tabella vengono elencati gli elementi "interrogabili" (queryables) ammissibili per le richieste di GetRecords e i metadati corrispondenti di cui al DM relativo al RNDT. Gli elementi interrogabili sono espressi nel formato indicato dalle specifiche OGC (nome qualificato preceduto dal prefisso "apiso"), così come devono essere riportati nelle richieste (le *queryables vengono gestite in modalità case-sensitive8* ).

| Elementi interrogabili (queryables) |  |
|---|---|
| apiso:identifier |  |
| apiso:language |  |
| apiso:ParentIdentifier |  |
| apiso:type |  |
| apiso:title |  |
| apiso:CreationDate |  |
| apiso:PublicationDate |  |
| apiso:RevisionDate |  |
| apiso:ResourceIdentifier |  |
| apiso:abstract |  |
| apiso:subject |  |
| apiso:OrganisationName |  |
| apiso:ResponsiblePartyRole |  |
| apiso:Denominator |  |
| apiso:DistanceValue |  |
| apiso:DistanceUOM |  |
| apiso:TopicCategory |  |
| apiso:ConditionApplyingToAccessAndUse |  |
| apiso:AccessConstraints |  |
| apiso:OtherConstraints |  |
| apiso:Classification |  |
| apiso:TempExtent_begin |  |
| apiso:TempExtent_end |  |
| apiso:lineage |  |
| apiso:SpecificationTitle |  |
| apiso:SpecificationDate |  |
| apiso:SpecificationDateType |  |

#### Metadato RNDT

Identificatore del file (tab. I-1 DM) Lingua dei metadati (tab. I-2 DM) Id file precedente (tab. I-4 DM) Livello gerarchico (tab. I-5 DM) Titolo (tab. I-10 DM) Data con Tipo Data = 'Creazione' (tab. I-11.1 DM) Data con Tipo Data = 'Pubblicazione' (tab. I-11.1 DM) Data con Tipo Data = 'Revisione' (tab. I-11.1 DM) Identificatore (tab. I-14 DM) Descrizione (tab. I-17 DM) Parola chiave (tab. I-18.1 DM) Punto di contatto - Nome dell'Ente (tab. I-19.1 DM) Punto di contatto - Ruolo (tab. I-19.2 DM) Risoluzione spaziale - Scala equivalente (tab. I-21.1 DM) Risoluzione spaziale - Distanza (tab. I-21.2 DM) Risoluzione spaziale - Distanza (tab. I-21.2 DM) Categoria tematica (tab. I-24 DM) Limitazione d'uso (tab. I-26 DM) Vincoli di accesso (tab. I-27 DM) Altri vincoli (tab. I-29 DM) Vincoli di sicurezza (tab. I-24 DM) Estensione temporale - Data inizio (tab. I-33.1 DM) Estensione temporale - Data fine (tab. I-33.2 DM) Genealogia (tab. I-36 DM) Conformità: specifiche - Titolo (tab. I-37.1 DM) Conformità: specifiche - Data (tab. I-37.2 DM) Conformità: specifiche - Tipo Data (tab. I-37.3 DM)

8 Come indicato in [CSW ISO AP], paragrafo 7.2.4, nota 12 a piè di pagina e nel paragrafo 8.2.2.1.1.

-----

| apiso:degree | Conformità: grado (tab. I-38 DM) |
|---|---|
| apiso:ServiceType | Tipo di servizio (tab. V-17 DM) |
| apiso:AnyText | --- |

**Tab. 3 - Elementi interrogabili (queryables) nel servizio di ricerca del RNDT**