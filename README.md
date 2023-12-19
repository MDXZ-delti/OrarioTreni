# ViaggiaTreno

Esploriamo le [API di ViaggiaTreno][API]. Le richieste sono tutte di tipo GET e il base-uri è <http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/>.

[API]: http://www.viaggiatreno.it/infomobilita/rest-jsapi "API di ViaggiaTreno"

## Casi d'uso

### Ricerca stazione

Quando cerchiamo informazioni su una stazione, vogliamo vedere quali sono i treni in partenza e in arrivo (numero treno e stazione di arrivo/di partenza), da quale binario partono e se sono in ritardo.

Per fare ciò, possiamo digitare le prime lettere della stazione e ottenere una lista di stazioni che iniziano con quelle lettere tramite l'endpoint `autocompletaStazione`.
Una volta scelta la stazione, chiamiamo `partenze` o `arrivi` con l'orario che ci interessa.
Il risultato di queste chiamate dovrebbe bastare per ottenere le informazioni che ci interessano, ma il campo `ritardo` (espresso in minuti) non sembra essere affidabile.

Possiamo verificare lo stato effettivo del treno chiamando `andamentoTreno`, che ci darà anche informazioni sul suo itinerario. Qui campo `ritardo` è più affidabile, anche se bisognerebbe confrontare quello riportato "ad alto livello" con quello riportato per ogni fermata. Per ogni fermata dell'itinerario abbiamo a disposizone (non sempre ovviamente) il binario e gli orari. Possiamo quindi fornire più informazioni, ad esempio controllando se un treno che sarebbe dovuto partire da un'altra stazione è effettivamente partito o meno.

Dovrei controllare se le informazioni relative ai binari riportate da `partenze` e `arrivi` sono affidabili; al momento, nel dubbio, uso quelle riportate da `andamentoTreno`.
Dovrei anche controllare se è possibile capire se un treno è partito dalla sua stazione di partenza senza scorrere tutte le fermate.

### Ricerca itinerario

Prendiamo il treno per andare da un posto all'altro. Ci affidiamo a ViaggiaTreno per trovare le possibili soluzioni di viaggio.

Selezioniamo la stazione di partenza e quella di arrivo: chiamiamo `autocompletaStazione` (ci servono i codici delle stazioni di partenza e di arrivo) e scegliamo un orario.
Cerchiamo un itinerario con `soluzioniViaggioNew` e scegliamo quello che ci interessa.
Vediamo per quali stazioni passa il treno, a che binario si ferma e se è in ritardo (forse lo vediamo anche da `soluzioniViaggioNew`, devo verificare) chiamando `andamentoTreno`. Tutto molto bello ma ancora in fase di sviluppo.

## Possibili _endpoint_

- [`autocompletaStazione`, `autocompletaStazioneImpostaViaggio` e `autocompletaStazioneNTS`](#autocompletastazione-autocompletastazioneimpostaviaggio-e-autocompletastazionents)
- [`partenze` e `arrivi`](#partenze-e-arrivi)
- [`cercaNumeroTrenoTrenoAutocomplete` e `cercaNumeroTreno`](#cercanumerotrenotrenoautocomplete-e-cercanumerotreno)
- [`dettaglioStazione`](#dettagliostazione)
- [`andamentoTreno`](#andamentotreno)
- [`elencoStazioni`](#elencostazioni)
- [`soluzioniViaggioNew`](#soluzioniviaggionew)

Quelli che chiamo parametri vanno aggiunti dopo l'endpoint, separati da un `/`.

### `autocompletaStazione`, `autocompletaStazioneImpostaViaggio` e `autocompletaStazioneNTS`

> **Parametri**:
>
> 1. `str`: nome (anche parziale) della stazione di cui si vuole sapere il codice

La risposta è nel formato `NOME_STAZIONE|CODICE_STAZIONE`.

Per ottenere tutte le stazioni possiamo chiamare `autocompletaStazione*` con tutte le lettere dell'alfabeto, una per volta. Vediamo che non ci sono duplicati.
Tuttavia, `autocompletaStazione` ritorna un risultato in più rispetto ad `autocompletaStazioneImpostaViaggio`: "ROMA TIBURTINA PIAZZALE EST|S08226".
`autocompletaStazioneNTS` riporta numerosi risultati in più, anche se ci sono diverse stazioni tornate dalle altre chiamate che non sono presenti in `autocompletaStazioneNTS` (ma molte sembrano essere grafie alternative, magari con o senza gli spazi attorno ai trattini).
C'è una differenza fondamentale tra i risultati delle prime due chiamate e quelli della terza: il codice riportato dai primi due è composto da una S seguita da 5 numeri (regex `S\d{5}`), mentre quello riportato dalla terza è composto dal numero 83 seguito da 7 numeri (regex `83\d{7}`).
L'83 è il [codice RICS](https://uic.org/support-activities/it/rics) privato degli zeri che identifica Ferrovie dello Stato Italiane SpA[^1], mentre le cifre seguenti identificano la stazione con zeri di padding. Anche dopo la S possono seguire zeri di padding rispetto al codice effettivo. I codici effettivi dovrebbero essere i [codici ENEE](https://uic.org/support-activities/it/location-codes-enee), ma ce ne sono alcuni strani (tipo quelli senza zeri di padding). È possibile che siano invece codici del [Central Reference File Database](https://rne.eu/it/rne-applications/ccs/crd/#:~:text=The%20Central%20Reference%20File%20Database,makes%20them%20available%20to%20users.).

### `partenze` e `arrivi`

> **Parametri**:
>
> 1. `str`: codice della stazione di cui si vogliono sapere le partenze/arrivi
> 2. `str`: data in uno dei formati specificati qui sotto

Per quanto riguarda il formato dell'ora da passare `partenze`/`arrivi`, abbiamo le seguenti possibilità:

- `%a %b %d %Y %T` (es. `Mon Jun 24 2019 18:00:00`)
- `%a %b %d %Y %T UTC {offset}`
- `%a %b %d %Y %T GMT {offset}`

`{offset}` è un placeholder per l'offset rispetto all'UTC. È una stringa formata
da un segno (`+` o `-`) seguito da un numero di cifre che va da 1 a 4.
Al posto degli spazi è possibile mettere una qualsiasi combinazione di caratteri purché il parsing riesca ad essere effettuato correttamente.
Non tutti i caratteri sono graditi al parser: vanno bene spazi, virgole e trattini (ma il trattino tra `%Y` e `%T` no) mentre trattini bassi no.
Solo nel primo caso non è possibile aggiungere spazzatura alla fine della stringa.
Stringhe valide sono, ad esempio:

- `Mon Jun 24 2019 18:00:00`
- `Mon, Jun 24 2019 18:00:00 GMT+0100 (Central European Time)`
- `Mon,Jun24,   ,--->?,?---,,,, 2019,18:00:00GMT+0100klkliniohhknuibiuudtrc`

Chiamando `partenze`, abbiamo i seguenti campi di interesse:

```json
{
  "numeroTreno": "numero del treno",
  "compNumeroTreno": "nome del treno (es. REG 2629)",
  "inStazione": "true o false",
  "haCambiNumero": "dice se cambia nome",
  "binarioProgrammatoPartenzaDescrizione": "binario programmato",
  "binarioEffettivoPartenzaDescrizione": "binario effettivo",
  "destinazione": "nome testuale della destinazione del treno",
  "dataPartenzaTreno": "data di partenza in millisecondi dalla Epoch",
  "codOrigine": "id della stazione di origine",
  "ritardo": "ritardo in minuti (spesso a 0 quando il treno è in ritardo, usare quello di andamentoTreno)"
}
```

### `cercaNumeroTrenoTrenoAutocomplete` e `cercaNumeroTreno`

`cercaNumeroTrenoTrenoAutocomplete` restituisce delle righe della seguente forma:

```text
NO_TRENO - STAZIONE_DI_PARTENZA|NO_TRENO-CODICE_STAZIONE-DATA_PARTENZA
```

`cercaNumeroTreno` restituisce un oggetto così fatto:

```json
{
  "numeroTreno": "numero del treno",
  "codLocOrig": "codice stazione di partenza",
  "descLocOrig": "nome della stazione di partenza",
  "dataPartenza": "data di partenza",
  "corsa": "identificativo corsa",
  "h24": "true o false"
}
```

### `dettaglioStazione`

L'oggetto ritornato da `dettaglioStazione` è così fatto:

```jsonc
{
  // 4 significa che è fuori regione, 3 è normale
  "tipoStazione": "numero che identifica il tipo",
  "lat": "latitudine della stazione",
  "lon": "longitudine della stazione",
  "localita": {
    "nomeBreve": "nome della stazione"
  }
}
```

### `andamentoTreno`

> **Parametri**:
>
> 1. `int`: id della stazione di partenza
> 2. `int`: numero del treno
> 3. `int`: data di partenza del treno in millisecondi dalla Epoch

La risposta di `andamentoTreno` è l'oggetto che segue (non completo), i cui campi si riferiscono alla tratta nel complesso. È un'estensione dell'oggetto ritornato da `partenze`/`arrivi`:

```jsonc
{
    "orarioPartenza": "timestamp orario partenza programmato",
    "orarioArrivo": "timestamp orario arrivo a destinazione programmato",

    // I seguenti campi non sono presenti in formato %s%N
    "compoOrarioPartenzaZeroEffettivo": "orario partenza dalla prima stazione effettivo",
    "compOrarioArrivoZeroEffettivo": "orario arrivo a destinazione effettivo",

    "oraUltimoRilevamento": "timestamp ora ultimo rilevamento",
    "stazioneUltimoRilevamento": "nome stazione ultimo rilevamento",

    // Cambi numerazione del treno
    "haCambiNumero": "true o false, ma non c'è da fidarsi perché è sempre a false",
    "cambiNumero": [
        {
            "nuovoNumeroTreno": "nuovo numero del treno",
            "stazione": "stazione in cui avviene il cambio"
        }
    ],

    "fermate": [
        {
            "id": "codice identificativo della stazione presso della fermata",
            "programmata": "timestamp fermata programmata",
            "effettiva": "timestamp fermata effettiva",
            "partenza_teorica": "timestamp partenza teorica",
            "arrivo_teorico": "timestamp arrivo teorico",
            "partenzaReale": "timestamp partenza reale",
            "arrivoReale": "timestamp arrivo reale",
            "ritardo": "ritardo in minuti",
            "ritardoPartenza": "ritardo in minuti",
            "ritardoArrivo": "ritardo in minuti",
            "tipoFermata": "può essere P, F o A"
        }
    ],

    "compDurata": "durata del viaggio dalla stazione di partenza a quella di arrivo",
    "idOrigine": "id della stazione di origine",
    "ritardo", "ritardo in minuti",
}
```

Il formato di compDurata è `h:m`, ad esempio `1:6` (1 ora e 6 minuti).
È poco utile perché si riferisce al viaggio nel complesso, non alle tratte singole che lo compongono (es. Milano-Genova e non Pavia-Tortona).
Inoltre potrebbe essere sbagliato, ad esempio su tratte di durata superiore a 24 ore.

Si noti che i treni che cambiano numero sono lo stesso treno. Anche se il numero cambia in una certa stazione, la stazione di origine del treno è la stessa.

In `fermate`, il campo `ritardo` ha il valore di `ritardoPartenza` se `tipoFermata` è `P` (ovvero se la "fermata" è la stazione di partenza del treno), di `ritardoArrivo` altrimenti.

### `elencoStazioni`

`elencoStazioni` ritorna un array di oggetti così fatti singolarmente:

```json
{
  "codReg": "codice della regione",
  "tipoStazione": "numero in [1, 4] che identifica il tipo (da decifrare)",
  "dettZoomStaz": [
    {
      "codiceStazione": "codice identificativo della stazione (sempre uguale a codStazione)",
      "zoomStartRange": "int in [6, 10]",
      "zoomStopRange": "int in [6, 10]",
      "pinpointVisibile": "bool",
      "pinpointVisible": "bool",
      "labelVisibile": "bool",
      "labelVisible": "bool",
      "codiceRegione": "sempre null"
    }
  ],
  "pstaz": [], // Sempre vuoto
  "mappaCitta": {
    "urlImagePinpoint": "sempre stringa vuota",
    "urlImageBaloon": "sempre stringa vuota"
  },
  "codiceStazione": "codice identificativo della stazione",
  "codStazione": "sempre identico a codiceStazione",
  "lat": "latitudine della stazione",
  "lon": "longitudine della stazione",
  "latMappaCitta": "quasi sempre 0.0, vedi nota",
  "lonMappaCitta": "quasi sempre 0.0, vedi nota",
  "localita": {
    "nomeLungo": "nome lungo",
    "nomeBreve": "nome breve",
    "label": "etichetta (es. Venezia o Carbonia Sebariu), non sempre presente",
    "id": "id della stazione"
  },
  "esterno": "bool",
  "offsetX": "int",
  "offsetY": "int",
  "nomeCitta": "nome della città"
}
```

Se scrivo qualcosa di fianco a un campo vuol dire che è sempre presente; se non è così lo specifico.

Se `codStazione` (e quindi `codiceStazione`) inizia per `F`, è sicuro che `tipoStazione` sia `4`
e che `nomeLungo`, `nomeBreve` e `nomeCitta` siano uguali a `codStazione` e che `label` sia vuoto.
Non è vero il contrario: ci sono stazione di tipo `4` con nomi comprensibili da un umano.

`dettZoomStaz` può essere un array vuoto e può avere più di un oggetto.

`latMappaCitta` e `lonMappaCitta` sono sempre a `0.0` tranne che in tre casi: due sono identici tra
loro e si ottengono chiamando `elencoStazioni(0)` e l'altro si ottiene chiamando `elencoStazioni(8)`.
Differisce dai primi due solo per l'assenza di oggetti nell'array `dettZoomStaz`, che i primi due
vedono popolato. Si tratta sempre della stessa stazione, ovvero l'AV di Reggio Emilia (codice S05254).
`latMappaCitta` e `lonMappaCitta`, per questa stazione, hanno valori diversi da `lat` e `lon`,
ma non so cosa rappresentino.

Una nota riguardo ai nomi: `nomeLungo` è sempre in maiuscolo, tranne che per la stazione "Dev.Int. DD/AV" (codice S08220).
In ben 13 casi (18 se si contano i duplicati), `nomeLungo` è più corto di `nomeBreve`.

### `soluzioniViaggioNew`

> **Parametri**:
>
> 1. `str`: codice della stazione di partenza
> 2. `str`: codice della stazione di arrivo
> 3. `str`: data nel formato `YYYY-MM-DDTHH:MM:SS*`

## Tabella dei codici delle regioni

| Codice | Regione                       |
| ------ | ----------------------------- |
| 0      | Italia                        |
| 1      | Lombardia                     |
| 2      | Liguria                       |
| 3      | Piemonte                      |
| 4      | Valle d'Aosta                 |
| 5      | Lazio                         |
| 6      | Umbria                        |
| 7      | Molise                        |
| 8      | Emilia Romagna                |
| 9      | Trentino-Alto Adige           |
| 10     | Friuli-Venezia Giulia         |
| 11     | Marche                        |
| 12     | Veneto                        |
| 13     | Toscana                       |
| 14     | Sicilia                       |
| 15     | Basilicata                    |
| 16     | Puglia                        |
| 17     | Calabria                      |
| 18     | Campania                      |
| 19     | Abruzzo                       |
| 20     | Sardegna                      |
| 21     | Provincia autonoma di Trento  |
| 22     | Provincia autonoma di Bolzano |

`datiMeteo` restituisce un errore se chiamata col codice 9 (Trentino-Alto Adige).

[^1]: Una lista completa si può trovare [qui](https://www.cit-rail.org/media/files/appendix_circular_letter_10_2021_list_of_codes_2021-05-17.pdf).
