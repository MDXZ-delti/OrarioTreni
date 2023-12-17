# ViaggiaTreno

Esploriamo le [API di ViaggiaTreno][API]. Le richieste sono tutte di tipo GET e il base-uri è <http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/>.

[API]: http://www.viaggiatreno.it/infomobilita/rest-jsapi (API di ViaggiaTreno)

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

## Possibili *endpoint*

Quelli che chiamo "parametri" vanno aggiunti dopo l'endpoint, separati da un `/`. Per comodità, uso la notazione funzionale. Sono riportati sono gli endpoint che mi interessano.

| Endpoint | Descrizione parametri | Risposta |
| -------- | --------- | -------- |
| `autocompletaStazione(p)` | `p` è il nome della stazione, parziale o completo | Lista di stazioni che iniziano con `p` con relativo codice identificativo |
| `dettaglioStazione(s, r)` | `s` è il codice della stazione, `r` è il codice della regione | Informazioni sulla stazione |
| `regione(s)` | `s` è il codice della stazione | Codice della regione |
| `partenze(s, t)` e `arrivi(s, t)` | `s` è il codice della stazione, `t` è l'orario nel formato `%a %b %d %Y %T GMT%z (%Z)` | Lista dei treni in partenza/in arrivo |
| `andamentoTreno(s, n,  d)` | `s` è il codice della stazione di partenza, `n` è il numero del treno, `d` è la data di partenza espressa in millisecondi dalla Epoch | Informazioni sul treno |
| `soluzioniViaggioNew(p, a, d)` | `p` ed `a` sono i codici senza la S iniziale delle stazioni di partenza e di arrivo, `d` è la data nel formato `%FT%H:%M:%S` | Lista di itinerari |
| `cercaNumeroTrenoTrenoAutocomplete(n)` | `n` è il numero del treno | Informazioni testuali sul treno |
| `cercaNumeroTreno(n)` | `n` è il numero del treno | Informazioni sul treno |

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
    "ritardo": "ritardo in minuti (spesso a 0 quando il treno è in ritardo, usare quello di andamentoTreno)",
}
```

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

Di seguito la tabella dei codici delle regioni:

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
| 21     | Provincia autonoma di Treno   |
| 22     | Provincia autonoma di Bolzano |

Il Trentino-Alto Adige (9) non è da usare con l'endpoint `datiMeteo`: non è mappata correttamente da [viaggiatreno.it][VT].

[VT]: http://www.viaggiatreno.it (Viaggia Treno)
