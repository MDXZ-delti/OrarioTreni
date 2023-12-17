#!/usr/bin/env python

import json
import logging
from argparse import ArgumentParser, BooleanOptionalAction
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, time, timedelta, timezone
from pathlib import Path

import inquirer  # type: ignore
import requests
from prettytable import PrettyTable

# TODO:
# - Handle the case where the train does not have all the stops (e.g. Saronno)
# - Add "trip duration" (both scheduled and estimated); it has to be calculated

CLEAR = "\x1b[2J"

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
UNDERSCORE = "\x1b[4m"
BLINK = "\x1b[5m"
REVERSE = "\x1b[7m"
HIDDEN = "\x1b[8m"
STRIKETHROUGH = "\x1b[9m"

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

CET = timezone(timedelta(seconds=3600), 'CET')

regions: dict[int, str] = {
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
    base_url = "http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"
    url = f'{base_url}/{method}/{"/".join(str(p) for p in params)}'

    r = requests.get(url)

    if r.status_code != 200:
        logging.error(f'Error {r.status_code} while calling {url}: {r.text}')
        return None

    if (logging.getLogger().getEffectiveLevel() == logging.DEBUG):
        dt = datetime.strptime(
            r.headers['Date'], '%a, %d %b %Y %H:%M:%S %Z').strftime('%Y-%j %X')
        filename = f'{dt} {method}({", ".join(str(p) for p in params)})'
        Path('responses').mkdir(parents=True, exist_ok=True)
        with open(f"responses/{filename}.json", "w") as f:
            json.dump(r.json(), f, indent=2)
            f.write('\n')

    return r.json() if 'json' in r.headers['Content-Type'] else r.text


def statistiche(timestamp: int):
    return get("statistiche", timestamp)


def autocompletaStazione(text: str) -> str | None:
    return get("autocompletaStazione", text)


def cercaStazione(text: str):
    return get("cercaStazione", text)


def dettaglioStazione(codiceStazione: str, codiceRegione: int):
    return get("dettaglioStazione", codiceStazione, codiceRegione)


def regione(codiceStazione: str) -> int | None:
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


class Duration(timedelta):
    def __new__(cls, td: timedelta) -> 'Duration':
        return super().__new__(cls, td.days, td.seconds, td.microseconds)

    def __init__(self, td: timedelta) -> None:
        self.hours: int = int(self.total_seconds() // 3600) % 24
        self.minutes: int = int(self.total_seconds() // 60) % 60

    def __str__(self) -> str:
        if (self.days > 0):
            return f'{self.days}d{self.hours:02}h{self.minutes:02}'
        elif (self.hours > 0):
            return f'{self.hours}h{self.minutes:02}'
        else:
            return f'{self.minutes} min'


class Train:
    """
    A train is identified by its origin station, its number and its departure date.
    """

    def __init__(self, data) -> None:
        if (data['orarioPartenza'] is not None):
            departure_datetime: datetime = datetime.fromtimestamp(
                data['orarioPartenza'] / 1000).replace(tzinfo=CET)
            self.departure_date: date = departure_datetime.date()
            self.departure_time: time = departure_datetime.timetz()
        if (data['orarioArrivo'] is not None):
            arrival_datetime: datetime = datetime.fromtimestamp(
                data['orarioArrivo'] / 1000).replace(tzinfo=CET)
            self.arrival_date: date = arrival_datetime.date()
            self.arrival_time: time = arrival_datetime.timetz()

        # TODO: check with the departure time if the train has departed
        self.provenance: str = data['origine']  # Only in arrivi
        self.destination: str = data['destinazione']  # Only in partenze
        self.category: str = data['categoriaDescrizione'].strip()
        self.changes_number: bool = data['haCambiNumero']

        self.departed: bool = not data['nonPartito']
        self.in_station: bool = data['inStazione']  # Not sure what this means

        # Will be overwritten if andamentoTreno() works since it's more accurate
        self.delay: timedelta = timedelta(minutes=data['ritardo'])

        # Overwritten if andamentoTreno() works
        self.numbers: dict[str, int] = {
            data['codOrigine']: data['numeroTreno']
        }

        #############################
        ### andamentoTreno() data ###
        #############################

        at_data = andamentoTreno(
            data['codOrigine'], data['numeroTreno'], data['dataPartenzaTreno'])

        # If this happens, viaggiatreno.it is not provinding real-time data
        # Now I have to change everything, fuck me
        self.no_data = False
        if (not at_data):
            print(
                f"Trenitalia non sta fornendo dati in tempo reale per il treno {
                    self}\n"
                f"Parametri richiesta andamentoTreno: {
                    data['codOrigine']}/{data['numeroTreno']}/{data['dataPartenzaTreno']}"
            )
            self.no_data = True
            return

        self.origin_station: Station = Station(
            at_data['origine'], at_data['idOrigine'])

        if at_data['oraUltimoRilevamento'] is not None:
            self.last_update: datetime = datetime.fromtimestamp(
                at_data['oraUltimoRilevamento'] / 1000)

        # It might not be an actual station (e.g. "bivio")
        self.last_update_station: str = at_data['stazioneUltimoRilevamento']

        ### Update values with better data ###

        # 'ritardo' is the departure delay if the station is the
        # first of the journey, otherwise it's the arrival delay
        self.delay = timedelta(minutes=at_data['ritardo'])

        self.numbers = {
            self.origin_station.name: data['numeroTreno']
        }

        if (self.changes_number):
            for change in at_data['cambiNumero']:
                self.numbers[change['stazione']] = int(
                    change['nuovoNumeroTreno'])

        self.stops: list[Stop] = [Stop(stop) for stop in at_data['fermate']]

    def __str__(self) -> str:
        return f'{self.category} {"/".join(str(n) for n in self.numbers.values())}'


# This should probably inherit from Station.
# I could then call getDepartures or something from a Stop
class Stop:
    """Stop in a journey.

    Part of the response of the andamentoTreno() method carrying information about the platform, the delay, and the arrival/departure time.
    """

    def __init__(self, data) -> None:
        self.id: str = data['id']
        self.name: str = data['stazione']

        self.departure_delay: timedelta = timedelta(
            minutes=data['ritardoPartenza'])
        self.arrival_delay: timedelta = timedelta(
            minutes=data['ritardoArrivo'])
        self.delay: timedelta = timedelta(minutes=data['ritardo'])

        if (data['partenza_teorica'] is not None):
            self.scheduled_departure_datetime: datetime = datetime.fromtimestamp(
                data['partenza_teorica'] / 1000).replace(tzinfo=CET)

        if (data['partenzaReale'] is not None):
            self.actual_departure_datetime: datetime = datetime.fromtimestamp(
                data['partenzaReale'] / 1000).replace(tzinfo=CET)

        if (data['arrivo_teorico'] is not None):
            self.scheduled_arrival_datetime: datetime = datetime.fromtimestamp(
                data['arrivo_teorico'] / 1000).replace(tzinfo=CET)

        if (data['arrivoReale'] is not None):
            self.actual_arrival_datetime: datetime = datetime.fromtimestamp(
                data['arrivoReale'] / 1000).replace(tzinfo=CET)

        # Note: some of the data about the platform might be available under partenze
        self.scheduled_departure_platform: str = data['binarioProgrammatoPartenzaDescrizione']
        self.actual_departure_platform: str = data['binarioEffettivoPartenzaDescrizione']
        self.scheduled_arrival_platform: str = data['binarioProgrammatoArrivoDescrizione']
        self.actual_arrival_platform: str = data['binarioEffettivoArrivoDescrizione']

        # If the actual departure platform is available and the train has not departed yet, the train is in the station
        self.train_in_station_if_not_departed: bool = self.actual_departure_platform is not None

        if self.actual_departure_platform is None and self.scheduled_departure_platform is None:
            self.actual_departure_platform = "N/A"

        if self.actual_departure_platform is None:
            self.actual_departure_platform = self.scheduled_departure_platform

        if self.scheduled_departure_platform is None:
            self.scheduled_departure_platform = self.actual_departure_platform

        self.departure_platform_has_changed: bool = self.actual_departure_platform != self.scheduled_departure_platform

        if self.actual_arrival_platform is None and self.scheduled_arrival_platform is None:
            self.actual_arrival_platform = "N/A"

        if self.actual_arrival_platform is None:
            self.actual_arrival_platform = self.scheduled_arrival_platform

        if self.scheduled_arrival_platform is None:
            self.scheduled_arrival_platform = self.actual_arrival_platform

        self.arrival_platform_has_changed: bool = self.actual_arrival_platform != self.scheduled_arrival_platform


class Station:
    # TODO: fix this (it should have an id, otherwise for each call to get* I have to call cercaStazione() again
    def __init__(self, partialName: str, id: str | None = None) -> None:
        if (id is not None):
            self.id: str = id
            self.name: str = partialName
            return

        r = cercaStazione(partialName)

        if (len(r) == 0):
            print('Nessuna stazione trovata')
            return

        # TODO: let the user choose the station (e.g. "Ancona")
        if (len(r) == 1) or (partialName.upper() in (station['nomeLungo'] for station in r)):
            self.name = str(r[0]['nomeLungo'])
            self.id = str(r[0]['id'])
            return

        guesses = tuple((station['nomeLungo'], station['id']) for station in r)
        choice = inquirer.list_input(
            message='Seleziona la stazione',
            choices=guesses
        )
        self.name = next(s[0] for s in guesses if s[1] == choice)
        self.id = choice

    def __str__(self) -> str:
        return f'Stazione di {self.name}'

    def getDepartures(self, dt: datetime):
        return partenze(self.id, dt.strftime('%a %b %d %Y %H:%M:%S GMT%z (%Z)'))

    def getArrivals(self, dt: datetime):
        return arrivi(self.id, dt.strftime('%a %b %d %Y %H:%M:%S GMT%z (%Z)'))

    def getJourneySolutions(self, other: 'Station', dt: datetime):
        return soluzioniViaggioNew(self.id[1:], other.id[1:], dt.strftime('%FT%T'))

    def showDepartures(self, dt: datetime) -> None:
        """Prints the departures from the station.

        Gets the actual delay and platform by querying the API (andamentoTreno) for each train.
        """
        print(f'{BOLD}Partenze da {self.name}{RESET}')

        departures = self.getDepartures(dt)
        if not departures:
            print('Nessun treno in partenza')
            return

        table = PrettyTable()
        table.field_names = ['Treno', 'Destinazione',
                             'Partenza', 'Ritardo', 'Binario']

        with ThreadPoolExecutor(len(departures)) as pool:
            # Calls Train(d) for each d in departures where d is JSON data
            futures = pool.map(Train, departures)

            for train in futures:
                minutes = int(train.delay.total_seconds() // 60)
                if minutes > 0:
                    delay = f'{RED}{minutes:+} min{RESET}'
                elif minutes < 0:
                    delay = f'{GREEN}{minutes:+} min{RESET}'
                else:
                    if train.departed:
                        delay = 'In orario'
                    else:
                        delay = 'Not enough data'

                if train.no_data:
                    table.add_row([f'{YELLOW}{train}{RESET}',
                                   f'{YELLOW}{train.destination}{RESET}',
                                   f'{YELLOW}{train.departure_time.strftime('%H:%M')}{
                        RESET}',
                        f'{YELLOW}{delay}{RESET}',
                        f'{YELLOW}No real-time info{RESET}'])
                    continue

                ### Update values with better data ###

                for s in train.stops:
                    if s.id == train.origin_station.id:
                        origin: Stop = s
                    if s.id == self.id:
                        stop: Stop = s

                if train.delay == timedelta(minutes=0):
                    # Those two are basically the same. "In stazione" means that
                    # the train is in the station from which showDepartures() is
                    # called and it has not departed yet. "Non partito" means
                    # that the train is in the station from which it departs and
                    # it has not departed yet.
                    if not train.departed and (origin.train_in_station_if_not_departed or origin.departure_platform_has_changed):
                        if dt > origin.scheduled_departure_datetime:
                            delay = f'{RED}Non partito{RESET}'
                        else:
                            delay = f'Non partito'
                    if not train.departed and (stop.train_in_station_if_not_departed or stop.departure_platform_has_changed):
                        if dt > stop.scheduled_departure_datetime:
                            delay = f'{RED}In stazione{RESET}'
                        else:
                            delay = f'In stazione'

                # Departure platform relative to the selected station
                if stop.departure_platform_has_changed:
                    departure_platform = f'{BLUE}{
                        stop.actual_departure_platform}{RESET}'
                else:
                    departure_platform = stop.actual_departure_platform

                table.add_row([train,
                               train.destination,
                               train.departure_time.strftime('%H:%M'),
                               delay,
                               departure_platform])

            print(table)

    def showArrivals(self, dt: datetime) -> None:
        """Prints the departures from the station.

        Gets the actual delay and platform by querying the API (andamentoTreno) for each train.
        """
        print(f'{BOLD}Arrivi a {self.name}{RESET}')

        arrivals = self.getArrivals(dt)
        if not arrivals:
            print('Nessun treno in arrivo')
            return

        table = PrettyTable()
        table.field_names = ['Treno', 'Provenienza',
                             'Arrivo', 'Ritardo', 'Binario']

        with ThreadPoolExecutor(len(arrivals)) as pool:
            # Calls Train(d) for each d in arrivals where d is JSON data
            futures = pool.map(Train, arrivals)

            for train in futures:
                minutes = int(train.delay.total_seconds() // 60)
                if minutes > 0:
                    delay = f'{RED}{minutes:+} min{RESET}'
                elif minutes < 0:
                    delay = f'{GREEN}{minutes:+} min{RESET}'
                else:
                    if train.departed:
                        delay = 'In orario'
                    else:
                        delay = 'Not enough data'

                if train.no_data:
                    table.add_row([f'{YELLOW}{train}{RESET}',
                                   f'{YELLOW}{train.provenance}{RESET}',
                                   f'{YELLOW}{train.arrival_time.strftime('%H:%M')}{
                        RESET}',
                        f'{YELLOW}{delay}{RESET}',
                        f'{YELLOW}No real-time info{RESET}'])
                    continue

                ### Update values with better data ###

                # Select the current station
                for s in train.stops:
                    if s.id == train.origin_station.id:
                        origin: Stop = s
                    if s.id == self.id:
                        stop: Stop = s

                if train.delay == timedelta(minutes=0):
                    if not train.departed and (origin.train_in_station_if_not_departed or origin.departure_platform_has_changed):
                        if dt > origin.scheduled_departure_datetime:
                            delay = f'{RED}Non partito{RESET}'
                        else:
                            delay = f'Non partito'

                # Arrival platform relative to the selected station
                if stop.arrival_platform_has_changed:
                    arrival_platform = f'{BLUE}{
                        stop.actual_arrival_platform}{RESET}'
                else:
                    arrival_platform = stop.actual_arrival_platform

                table.add_row([train,
                               train.provenance,
                               train.arrival_time.strftime('%H:%M'),
                               delay,
                               arrival_platform])

            print(table)

    def showJourneySolutions(self, other: 'Station', dt: datetime) -> None:
        solutions = self.getJourneySolutions(other, dt)
        print(
            f'{BOLD}Soluzioni di viaggio da {self.name} a {other.name}{RESET}')
        for solution in solutions['soluzioni']:
            # TODO: create a proper Duration and calculate the total duration since the one in the response may be wrong
            # total_duration = solution['durata'].lstrip('0').replace(':', 'h')
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

                duration = Duration(
                    arrival_time_dt - departure_time_dt)

                print(
                    f'{departure_time}–{arrival_time} ({category}{" " if category else ""}{number}) [{duration}]')

                # Print a train change if present
                if (vehicle is not solution['vehicles'][-1]):
                    next_vehicle = solution['vehicles'][solution['vehicles'].index(
                        vehicle) + 1]
                    oa = datetime.fromisoformat(
                        vehicle['orarioArrivo'])
                    od = datetime.fromisoformat(
                        next_vehicle['orarioPartenza'])
                    change = Duration(od - oa)
                    print(
                        f'Cambio a {vehicle["destinazione"]} [{change}]')
            print()


class Stats:
    def __init__(self) -> None:
        self.dt: datetime = datetime.now(UTC)
        timestamp = int(self.dt.timestamp() * 1000)
        data = statistiche(timestamp)
        self.trains_today: int = data['treniGiorno']
        self.trains_now: int = data['treniCircolanti']

    def __str__(self) -> str:
        return (
            f'Numero treni in circolazione da mezzanotte: {
                self.trains_today}\n'
            f'Numero treni in circolazione ora: {self.trains_now}\n'
            f'{DIM}Ultimo aggiornamento: {self.dt.astimezone().strftime("%T")}{
                RESET}'
        )


if __name__ == "__main__":
    ap = ArgumentParser(description='Get information about trains in Italy')

    ap.add_argument('-v', '--version', action='version',
                    version='%(prog)s 0.1')
    ap.add_argument('-d', '--departures', metavar='STATION',
                    type=str, help='show departures from a station')
    ap.add_argument('-a', '--arrivals', metavar='STATION',
                    type=str, help='show arrivals to a station')
    ap.add_argument('-s', '--solutions', metavar=('DEPARTURE', 'ARRIVAL'),
                    type=str, nargs=2, help='show journey solutions from DEPARTURE to ARRIVAL')
    ap.add_argument(
        '--date', metavar="YYYY-MM-DD", type=str, help='date to use for the other actions; defaults to today')
    ap.add_argument(
        '--time', metavar="HH:MM", type=str, help='time to use for the other actions; defaults to now')
    ap.add_argument('--stats', action=BooleanOptionalAction,
                    help='show/don\'t show stats (defaults to True)', default=True)
    ap.add_argument('--log-level', metavar='LEVEL', type=str,
                    help='set the logging level (defaults to WARNING)', default='WARNING')

    ap.epilog = 'Departures and arrivals show trains from/to the selected station in a range from 15 minutes before to 90 minutes after the selected time.'

    args = ap.parse_args()

    # Check if the log level is valid
    if (args.log_level not in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')):
        print(
            f'Invalid log level: {RED}{args.log_level}{RESET} '
            '(valid values are: DEBUG, INFO, WARNING, ERROR, CRITICAL).'
        )

        exit(1)

    logging.basicConfig(level=args.log_level)

    if (args.stats):
        print(Stats())

    if (args.date):
        search_date = datetime.strptime(
            args.date, '%Y-%m-%d').astimezone().date()
    else:
        search_date = datetime.now(UTC).date()

    if (args.time):
        search_time = datetime.strptime(
            args.time, '%H:%M').astimezone().timetz()
    else:
        search_time = datetime.now(UTC).timetz()

    search_datetime = datetime.combine(search_date, search_time)

    if (args.departures):
        station = Station(args.departures)
        station.showDepartures(search_datetime)

    if (args.arrivals):
        station = Station(args.arrivals)
        station.showArrivals(search_datetime)

    if (args.solutions):
        departure_station = Station(args.solutions[0])
        arrival_station = Station(args.solutions[1])
        departure_station.showJourneySolutions(
            arrival_station, search_datetime)
