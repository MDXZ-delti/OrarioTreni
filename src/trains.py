#!/usr/bin/env python

import argparse
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import inquirer
import requests
from prettytable import PrettyTable

type hhmmTime = str
type msSinceEpoch = int
type Minute = int
type Platform = int | str  # It might be a string if it's "tronco"

# TODO:
# - Handle the case where the train does not have all the stops (e.g. Saronno).
# - Add "trip duration" (both scheduled and estimated); it has to be calculated
# - Use the field "nonPartito" under "partenze" (it seems correct)
# - Add the CLI option "--log-level" to set the logging level

base_url = "http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"
logging.basicConfig(level=logging.WARNING)

CLEAR = "\x1b[2J"

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
UNDERSCORE = "\x1b[4m"
BLINK = "\x1b[5m"
REVERSE = "\x1b[7m"
HIDDEN = "\x1b[8m"

BLACK = "\x1b[30m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
BLUE = "\x1b[34m"
MAGENTA = "\x1b[35m"
CYAN = "\x1b[36m"
WHITE = "\x1b[37m"
# Custom color with \x1B[38;2;R;G;Bm

BLACK_BG = "\x1b[40m"
RED_BG = "\x1b[41m"
GREEN_BG = "\x1b[42m"
YELLOW_BG = "\x1b[43m"
BLUE_BG = "\x1b[44m"
MAGENTA_BG = "\x1b[45m"
CYAN_BG = "\x1b[46m"
WHITE_BG = "\x1b[47m"
# Custom background color with \x1B[48;2;R;G;Bm

regions = {
    0: "Italia",
    1: "Lombardia",
    2: "Liguria",
    3: "Piemonte",
    4: "Valle d'Aosta",
    5: "Lazio",
    6: "Umbria",
    7: "Molise",
    8: "Emilia Romagna",
    9: "Trentino-Alto Adige",
    10: "Friuli-Venezia Giulia",
    11: "Marche",
    12: "Veneto",
    13: "Toscana",
    14: "Sicilia",
    15: "Basilicata",
    16: "Puglia",
    17: "Calabria",
    18: "Campania",
    19: "Abruzzo",
    20: "Sardegna",
    21: "Provincia autonoma di Treno",
    22: "Provincia autonoma di Bolzano"
}


def get(method: str, *params):
    """call the ViaggiaTreno API with the given method and parameters."""
    url = f'{base_url}/{method}/{"/".join(str(p) for p in params)}'

    r = requests.get(url)

    if r.status_code != 200:
        logging.error(f'Error {r.status_code} while calling {url}: {r.text}')
        return None

    filename = f'{method} ({", ".join(str(p)
                                      for p in params)}) [{r.headers["Date"]}]'
    if (logging.getLogger().getEffectiveLevel() == logging.DEBUG):
        Path('responses').mkdir(parents=True, exist_ok=True)
        with open(f"responses/{filename}.json", "w") as f:
            f.write(json.dumps(r.json(), indent=4))

    return r.json() if 'json' in r.headers['Content-Type'] else r.text


def statistiche(timestamp: int):
    return get("statistiche", timestamp)


def autocompletaStazione(text: str):
    return get("autocompletaStazione", text)


def cercaStazione(text: str):
    return get("cercaStazione", text)


def dettaglioStazione(codiceStazione: str, codiceRegione: int):
    return get("dettaglioStazione", codiceStazione, codiceRegione)


def regione(codiceStazione: str):
    return get("regione", codiceStazione)


def partenze(codiceStazione: str, orario: str):
    # orario's format is '%a %b %d %Y %H:%M:%S GMT%z (%Z)'
    return get("partenze", codiceStazione, orario)


def arrivi(codiceStazione: str, orario: str):
    # orario's format is '%a %b %d %Y %H:%M:%S GMT%z (%Z)'
    return get("arrivi", codiceStazione, orario)


def andamentoTreno(codOrigine: str, numeroTreno: int, dataPartenza: int):
    # dataPartenza is in ms sine the Epoch
    return get("andamentoTreno", codOrigine, numeroTreno, dataPartenza)


def soluzioniViaggioNew(codLocOrig: str, codLocDest: str, date: str):
    # date's format is "%FT%T" and station codes don't have the starting 'S'
    return get("soluzioniViaggioNew", codLocOrig, codLocDest, date)


class Train:
    def __init__(self, data) -> None:
        # TODO: check with the departure time if the train has departed
        self.departed: bool = data['inStazione']
        self.departure_date: msSinceEpoch = data['dataPartenzaTreno']
        self.departure_time: hhmmTime = data['compOrarioPartenza']
        self.arrival_time: hhmmTime = data['compOrarioArrivo']
        self.origin: str = data['origine']
        self.destination: str = data['destinazione']
        self.origin_station: Station = Station(
            name=None, id=data['codOrigine'] or data['idOrigine'])
        self.category: str = data['categoriaDescrizione'].strip()
        self.number: int | str = data['numeroTreno']


# This should probably inherit from Train.
class Journey:
    def __init__(self, origin_station, train_number, departure_date) -> None:
        data = getJourneyInfo(origin_station, train_number, departure_date)

        if (not data):
            raise Exception('Trenitalia non sta fornendo aggiornamenti')

        self.last_update_time: msSinceEpoch = data['oraUltimoRilevamento']
        self.last_update_station: str = data['stazioneUltimoRilevamento']

        # 'ritardo' is the departure delay if the station is the
        # first of the journey, otherwise it's the arrival delay
        self.delay: Minute = data['ritardo']

        self.train_numbers: int | str = train_number
        if (data['haCambiNumero']):
            for change in data['cambiNumero']:
                self.train_numbers += '/' + change['nuovoNumeroTreno']

        self.stops: list[Stop] = [Stop(stop) for stop in data['fermate']]

    @classmethod
    def fromTrain(cls, train: Train) -> 'Journey':
        return cls(train.origin_station, train.number, train.departure_date)

    def __str__(self) -> str:
        return f'Dettagli del treno {self.train_numbers} con partenza da {self.origin_station} in data {self.departure_date}'


# This should probably inherit from Station.
# I could then call getDepartures or something from a Stop
class Stop:
    """Stop in a journey.

    Part of the response of the andamentoTreno() method carrying information about the platform, the delay, and the arrival/departure time.
    """

    def __init__(self, data) -> None:
        self.id: str = data['id']
        self.name: str = data['stazione']
        # Note: some of the data about the platform might be available under partenze
        self.scheduled_departure_platform: Platform = data['binarioProgrammatoPartenzaDescrizione']
        self.actual_departure_platform: Platform = data['binarioEffettivoPartenzaDescrizione']
        self.scheduled_arrival_platform: Platform = data['binarioProgrammatoArrivoDescrizione']
        self.actual_arrival_platform: Platform = data['binarioEffettivoArrivoDescrizione']
        self.departure_delay: Minute = data['ritardoPartenza']
        self.arrival_delay: Minute = data['ritardoArrivo']
        self.delay: Minute = data['ritardo']
        self.scheduled_departure_time: msSinceEpoch = data['partenza_teorica']
        self.actual_departure_time: msSinceEpoch = data['partenzaReale']
        self.scheduled_arrival_time: msSinceEpoch = data['arrivo_teorico']
        self.actual_arrival_time: msSinceEpoch = data['arrivoReale']

    def departurePlatformHasChanged(self) -> bool:
        return self.actual_departure_platform and self.actual_departure_platform != self.scheduled_departure_platform

    def arrivalPlatformHasChanged(self) -> bool:
        return self.actual_arrival_platform and self.actual_arrival_platform != self.scheduled_arrival_platform

    def getDeparturePlatform(self) -> str:
        """Get the actual departure platform if it's available, otherwise the scheduled one."""
        return self.actual_departure_platform if self.departurePlatformHasChanged() else self.scheduled_departure_platform

    def getArrivalPlatform(self) -> str:
        """Get the actual arrival platform if it's available, otherwise the scheduled one."""
        return self.actual_arrival_platform if self.arrivalPlatformHasChanged() else self.scheduled_arrival_platform


class Station:
    def __init__(self, name=None, id=None) -> None:
        self.name: str = name
        self.id: str = id

        if (name is None and id is None):
            name = inquirer.text('Inserisci il nome della stazione')

        if (id is None):
            r = cercaStazione(name)

            if (len(r) == 0):
                print('Nessuna stazione trovata')
                return

            if (len(r) == 1):
                self.name = r[0]['nomeLungo']
                self.id = r[0]['id']
                return

            for station in r:
                if (station['nomeLungo'] == name.upper()):
                    self.name = station['nomeLungo']
                    self.id = station['id']
                    return

            guesses = tuple((station['nomeLungo'], station['id'])
                            for station in r)
            choice = inquirer.list_input(
                message='Seleziona la stazione',
                choices=guesses
            )
            self.name = next(s[0] for s in guesses if s[1] == choice)
            self.id = choice

    def __str__(self) -> str:
        return f'Stazione di {self.name}'

    def getDepartures(self, date=None):
        if (date is None):
            date = datetime.now(UTC)
        if isinstance(date, int):
            date = datetime.fromtimestamp(date)
        if isinstance(date, datetime):
            date = date.strftime('%a %b %d %Y %H:%M:%S GMT%z (%Z)')
        return partenze(self.id, date)

    def getArrivals(self, date=None):
        if (date is None):
            date = datetime.now(UTC)
        if isinstance(date, int):
            date = datetime.fromtimestamp(date)
        if isinstance(date, datetime):
            date = date.strftime('%a %b %d %Y %H:%M:%S GMT%z (%Z)')
        return arrivi(self.id, date)

    def getJourneySolutions(self, other, time=None):
        codLocOrig = self.id[1:]
        codLocDest = other.id[1:]
        if (time is None):
            time = datetime.now(UTC)
        if isinstance(time, int):
            time = datetime.fromtimestamp(time)
        if isinstance(time, datetime):
            time = time.strftime('%FT%T')
        return soluzioniViaggioNew(codLocOrig, codLocDest, time)

    def showDepartures(self, date=None) -> None:
        """Prints the departures from the station.

        Gets the actual delay and platform by querying the API (andamentoTreno) for each train.
        """
        departures = [Train(d) for d in self.getDepartures(date)]
        print(f'{BOLD}Partenze da {self.name}{RESET}')

        table = PrettyTable()
        table.field_names = ['Treno', 'Destinazione',
                             'Partenza', 'Ritardo', 'Binario']

        if (len(departures) == 0):
            print('Nessun treno in partenza')
            return

        with ThreadPoolExecutor(len(departures)) as pool:
            futures = pool.map(Journey.fromTrain, departures)
            for (train, journey) in zip(departures, futures, strict=True):
                # Number changes are returned by andamentoTreno()
                # partenze() only says if the train has changed number
                train.numbers = journey.train_numbers

                # Get info relative to the selected station
                stop = next(s for s in journey.stops if s.id == self.id)

                # Departure platform relative to the selected station
                train.departure_platform = stop.getDeparturePlatform()

                # Try to get the delay from the stop.
                # If it's not available, use the one from the journey
                delay = stop.delay or journey.delay
                delay_text = f'{RED if delay > 0 else GREEN}{
                    delay:+} min{RESET}' if delay else ''

                table.add_row([f'{train.category} {train.number}',
                               train.destination,
                               train.departure_time,
                               delay_text,
                               train.departure_platform or ''])

            print(table)

    def showArrivals(self, date=None) -> None:
        """Prints the departures from the station.

        Gets the actual delay and platform by querying the API (andamentoTreno) for each train.
        """
        arrivals = [Train(d) for d in self.getArrivals(date)]
        print(f'{BOLD}Arrivi a {self.name}{RESET}')

        table = PrettyTable()
        # Provenienza is the origin station, Arrivo is the arrival time
        table.field_names = ['Treno', 'Provenienza',
                             'Arrivo', 'Ritardo', 'Binario']

        if (len(arrivals) == 0):
            print('Nessun treno in arrivo')
            return

        with ThreadPoolExecutor(len(arrivals)) as pool:
            futures = pool.map(Journey.fromTrain, arrivals)
            for (train, journey) in zip(arrivals, futures, strict=True):
                # Number changes are returned by andamentoTreno()
                # partenze() only says if the train has changed number
                train.numbers = journey.train_numbers

                # Get info relative to the selected station
                stop = next(s for s in journey.stops if s.id == self.id)

                # Arrival platform relative to the selected station
                train.arrival_platform = stop.getArrivalPlatform()

                # Try to get the delay from the stop.
                # If it's not available, use the one from the journey
                delay = stop.delay or journey.delay
                delay_text = f'{RED if delay > 0 else GREEN}{
                    delay:+} min{RESET}' if delay else ''

                table.add_row([f'{train.category} {train.number}',
                               train.origin,
                               train.arrival_time,
                               delay_text,
                               train.arrival_platform or ''])

            print(table)

    def showJourneySolutions(self, other, time=None) -> None:
        solutions = self.getJourneySolutions(other, time)
        print(
            f'{BOLD}Soluzioni di viaggio da {self.name} a {other.name}{RESET}')
        for solution in solutions['soluzioni']:
            total_duration = solution['durata'].lstrip('0').replace(':', 'h')
            for vehicle in solution['vehicles']:
                # Note: this field is empty in andamentoTreno, while "categoria" isn't
                # andamentoTreno has the field compNumeroTreno. I have to check whether that's always true and what's there when a train has multiple numbers
                category = vehicle['categoriaDescrizione']
                number = vehicle['numeroTreno']
                departure_time_dt = datetime.fromisoformat(
                    vehicle['orarioPartenza'])
                arrival_time_dt = datetime.fromisoformat(
                    vehicle['orarioArrivo'])
                departure_time = departure_time_dt.strftime('%H:%M')
                arrival_time = arrival_time_dt.strftime('%H:%M')

                def td_to_str(td: timedelta) -> str:
                    minutes = int(td.total_seconds()) // 60

                    if (minutes >= 60 * 24):
                        return f'{minutes // (60 * 24)}d{minutes % (60 * 24) // 60}h{minutes % 60:02}'
                    elif (minutes >= 60):
                        return f'{minutes // 60}h{minutes % 60:02}'
                    else:
                        return f'{minutes} min'

                duration = td_to_str(arrival_time_dt - departure_time_dt)

                print(
                    f'{departure_time}–{arrival_time} ({category}{" " if category else ""}{number}) [{duration}]')

                # Print a train change if present
                if (len(solutions['soluzioni']) > 1 and vehicle is not solution['vehicles'][-1]):
                    next_vehicle = solution['vehicles'][solution['vehicles'].index(
                        vehicle) + 1]
                    oa = datetime.fromisoformat(
                        vehicle['orarioArrivo'])
                    od = datetime.fromisoformat(
                        next_vehicle['orarioPartenza'])
                    change = td_to_str(od - oa)
                    print(
                        f'Cambio a {vehicle["destinazione"]} [{change}]')
            print("Durata totale:", total_duration)
            print()


def getStats(timestamp):
    """Query the endpoint <statistiche>."""
    if (timestamp is None):
        timestamp = datetime.now(UTC)
    if (isinstance(timestamp, datetime)):
        timestamp = int(timestamp.timestamp() * 1000)
    return statistiche(timestamp)


def showStats() -> None:
    """Show national statistics about trains."""
    now = datetime.now(UTC)
    r = statistiche(now)
    print(f'Numero treni in circolazione da mezzanotte: {r["treniGiorno"]}')
    print(f'Numero treni in circolazione ora: {r["treniCircolanti"]}')
    print(f'{DIM}Ultimo aggiornamento: {
          now.astimezone().strftime("%T")}\n{RESET}')


def getJourneyInfo(departure_station, train_number, departure_date):
    """Query the endpoint <andamentoTreno>."""
    return andamentoTreno(departure_station.id,
                          train_number, departure_date)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Get information about trains in Italy')

    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s 0.1')
    parser.add_argument('-d', '--departures', metavar='STATION', type=str,
                        help='show departures from a station')
    parser.add_argument('-a', '--arrivals', metavar='STATION', type=str,
                        help='show arrivals to a station')
    parser.add_argument('-s', '--solutions', metavar=('DEPARTURE',
                        'ARRIVAL'), type=str, nargs=2, help='show journey solutions from DEPARTURE to ARRIVAL')
    parser.add_argument(
        '-t', '--time', help='time to use for the other actions')
    parser.add_argument(
        '--stats', action=argparse.BooleanOptionalAction, help='show/don\'t show stats (defaults to True)', default=True)

    parser.epilog = 'Departures and arrivals show trains from/to the selected station in a range from 15 minutes before to 90 minutes after the selected time. If no time is specified, the current time is used.'

    args = parser.parse_args()

    if (args.stats):
        showStats()

    if (args.departures):
        station = Station(args.departures)
        station.showDepartures()

    if (args.arrivals):
        station = Station(args.arrivals)
        station.showArrivals()

    if (args.solutions):
        departure_station = Station(args.solutions[0])
        arrival_station = Station(args.solutions[1])
        departure_station.showJourneySolutions(arrival_station, args.time)
