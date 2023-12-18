#!/usr/bin/env python

__version__ = '0.1'
__author__ = 'Matteo Delton'

import logging
from argparse import ArgumentParser, BooleanOptionalAction
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, time, timedelta, timezone

import inquirer  # type: ignore
from prettytable import PrettyTable

from viaggiatreno import ViaggiaTreno

# TODO:
# - Handle the case where the train does not have all the stops (e.g. Saronno)
# - Add 'trip duration' (both scheduled and estimated); it has to be calculated

CLEAR = '\x1b[2J'

RESET = '\x1b[0m'
BOLD = '\x1b[1m'
DIM = '\x1b[2m'
UNDERSCORE = '\x1b[4m'
BLINK = '\x1b[5m'
REVERSE = '\x1b[7m'
HIDDEN = '\x1b[8m'
STRIKETHROUGH = '\x1b[9m'

BLACK = '\x1b[30m'
RED = '\x1b[31m'
GREEN = '\x1b[32m'
YELLOW = '\x1b[33m'
BLUE = '\x1b[34m'
MAGENTA = '\x1b[35m'
CYAN = '\x1b[36m'
WHITE = '\x1b[37m'
# Custom color with \x1B[38;2;R;G;Bm

BLACK_BG = '\x1b[40m'
RED_BG = '\x1b[41m'
GREEN_BG = '\x1b[42m'
YELLOW_BG = '\x1b[43m'
BLUE_BG = '\x1b[44m'
MAGENTA_BG = '\x1b[45m'
CYAN_BG = '\x1b[46m'
WHITE_BG = '\x1b[47m'
# Custom background color with \x1B[48;2;R;G;Bm

CET = timezone(timedelta(seconds=3600), 'CET')

vt = ViaggiaTreno()


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
            dep_datetime: datetime = datetime.fromtimestamp(
                data['orarioPartenza'] / 1000).replace(tzinfo=CET)
            # TODO: check if it corresponds to data['dataPartenzaTreno']
            self.dep_date: date = dep_datetime.date()
            self.dep_time: time = dep_datetime.timetz()
        if (data['orarioArrivo'] is not None):
            arr_datetime: datetime = datetime.fromtimestamp(
                data['orarioArrivo'] / 1000).replace(tzinfo=CET)
            self.arr_date: date = arr_datetime.date()
            self.arr_time: time = arr_datetime.timetz()

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

        at_data = vt.train_status(
            data['codOrigine'], data['numeroTreno'], data['dataPartenzaTreno'])

        # If this happens, viaggiatreno.it is not provinding real-time data
        self.no_data = False
        if (at_data is None):
            print(
                f'Trenitalia non sta fornendo dati in tempo reale per il treno {
                    self}\n'
                f'Parametri richiesta andamentoTreno: {
                    data["codOrigine"]}/{data["numeroTreno"]}/{data["dataPartenzaTreno"]}'
            )
            self.no_data = True
            return

        self.origin: Station = Station(
            at_data['origine'], at_data['idOrigine'])

        if at_data['oraUltimoRilevamento'] is not None:
            self.last_update: datetime = datetime.fromtimestamp(
                at_data['oraUltimoRilevamento'] / 1000)

        # It might not be an actual station (e.g. 'bivio'), but I'm not sure
        self.last_update_station: str = at_data['stazioneUltimoRilevamento']

        ### Update values with better data ###

        self.delay = timedelta(minutes=at_data['ritardo'])

        self.numbers = {self.origin.name: data['numeroTreno']}

        if (self.changes_number):
            for nc in at_data['cambiNumero']:
                self.numbers[nc['stazione']] = int(nc['nuovoNumeroTreno'])

        # TODO: check if there's work to do here
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

        self.dep_delay: timedelta = timedelta(minutes=data['ritardoPartenza'])
        self.arr_delay: timedelta = timedelta(minutes=data['ritardoArrivo'])
        self.delay: timedelta = timedelta(minutes=data['ritardo'])

        if (data['partenza_teorica'] is not None):
            self.scheduled_dep_datetime: datetime = datetime.fromtimestamp(
                data['partenza_teorica'] / 1000).replace(tzinfo=CET)

        if (data['partenzaReale'] is not None):
            self.actual_dep_datetime: datetime = datetime.fromtimestamp(
                data['partenzaReale'] / 1000).replace(tzinfo=CET)

        if (data['arrivo_teorico'] is not None):
            self.scheduled_arr_datetime: datetime = datetime.fromtimestamp(
                data['arrivo_teorico'] / 1000).replace(tzinfo=CET)

        if (data['arrivoReale'] is not None):
            self.actual_arr_datetime: datetime = datetime.fromtimestamp(
                data['arrivoReale'] / 1000).replace(tzinfo=CET)

        # TODO
        # If the previous stop has an actual arrival platform, this should be used
        # even if the actual departure platform is not yet available (maybe add
        # a check against the scheduled departure platform)
        # In order to do this, I must remove the assignment to self.actual_dep_platform
        # if it's None

        # Note: some of the data about the platform might be available under partenze
        self.scheduled_dep_platform: str = data['binarioProgrammatoPartenzaDescrizione']
        self.actual_dep_platform: str = data['binarioEffettivoPartenzaDescrizione']
        self.scheduled_arr_platform: str = data['binarioProgrammatoArrivoDescrizione']
        self.actual_arr_platform: str = data['binarioEffettivoArrivoDescrizione']

        self.dep_platform_confirmed: bool = self.actual_dep_platform is not None

        if self.actual_dep_platform is None and self.scheduled_dep_platform is None:
            self.actual_dep_platform = 'N/A'

        if self.actual_dep_platform is None:
            self.actual_dep_platform = self.scheduled_dep_platform

        if self.scheduled_dep_platform is None:
            self.scheduled_dep_platform = self.actual_dep_platform

        self.dep_platform_has_changed: bool = self.actual_dep_platform != self.scheduled_dep_platform

        self.arr_platform_confirmed: bool = self.actual_arr_platform is not None

        if self.actual_arr_platform is None and self.scheduled_arr_platform is None:
            self.actual_arr_platform = 'N/A'

        if self.actual_arr_platform is None:
            self.actual_arr_platform = self.scheduled_arr_platform

        if self.scheduled_arr_platform is None:
            self.scheduled_arr_platform = self.actual_arr_platform

        self.arr_platform_has_changed: bool = self.actual_arr_platform != self.scheduled_arr_platform


class Station:
    # TODO: fix this (it should have an id, otherwise for each call to get* I have to call cercaStazione() again
    def __init__(self, partialName: str, id: str | None = None) -> None:
        if (id is not None):
            self.id: str = id
            self.name: str = partialName
            return

        r = vt.find_station(partialName)

        if not r:
            print('Nessuna stazione trovata')
            return

        # TODO: let the user choose the station (e.g. 'Ancona')
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

    def show_departures(self, dt: datetime) -> None:
        """Prints the departures from the station.

        Gets the actual delay and platform by querying the API (andamentoTreno) for each train.
        """
        print(f'{BOLD}Partenze da {self.name}{RESET}')

        departures = vt.departures(self.id, dt)
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
                        # Not enough data to determine whether the train is in the station or not
                        delay = ''

                if train.no_data:
                    table.add_row([f'{YELLOW}{train}{RESET}',
                                   f'{YELLOW}{train.destination}{RESET}',
                                   f'{YELLOW}{train.dep_time.strftime('%H:%M')}{
                        RESET}',
                        f'{YELLOW}{delay}{RESET}',
                        f'{YELLOW}No real-time info{RESET}'])
                    continue

                ### Update values with better data ###

                for s in train.stops:
                    if s.id == train.origin.id:
                        origin: Stop = s
                    if s.id == self.id:
                        stop: Stop = s

                if train.delay == timedelta(minutes=0):
                    # Those two are basically the same. 'In stazione' means that
                    # the train is in the station from which showDepartures() is
                    # called and it has not departed yet. 'Non partito' means
                    # that the train is in the station from which it departs and
                    # it has not departed yet.
                    if not train.departed and (origin.dep_platform_confirmed or origin.dep_platform_has_changed):
                        if dt > origin.scheduled_dep_datetime:
                            delay = f'{RED}Non partito{RESET}'
                        else:
                            delay = f'Non partito'
                    if not train.departed and (stop.dep_platform_confirmed or stop.dep_platform_has_changed):
                        # It's possible that no info are currently available
                        if dt > stop.scheduled_dep_datetime:
                            delay = f'{RED}In stazione{RESET}'
                        else:
                            delay = f'In stazione'

                # Departure platform relative to the selected station
                if stop.dep_platform_has_changed:
                    dep_platform = f'{MAGENTA}{
                        stop.actual_dep_platform}{RESET}'
                else:
                    if stop.dep_platform_confirmed:
                        dep_platform = f'{
                            BLUE}{stop.actual_dep_platform}{RESET}'
                    else:
                        dep_platform = stop.actual_dep_platform

                table.add_row([train,
                               train.destination,
                               train.dep_time.strftime('%H:%M'),
                               delay,
                               dep_platform])

            print(table)

    def show_arrivals(self, dt: datetime) -> None:
        """Prints the departures from the station.

        Gets the actual delay and platform by querying the API (andamentoTreno) for each train.
        """
        print(f'{BOLD}Arrivi a {self.name}{RESET}')

        arrivals = vt.arrivals(self.id, dt)
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
                                   f'{YELLOW}{train.arr_time.strftime('%H:%M')}{
                        RESET}',
                        f'{YELLOW}{delay}{RESET}',
                        f'{YELLOW}No real-time info{RESET}'])
                    continue

                ### Update values with better data ###

                # Select the current station
                for s in train.stops:
                    if s.id == train.origin.id:
                        origin: Stop = s
                    if s.id == self.id:
                        stop: Stop = s

                if train.delay == timedelta(minutes=0):
                    if (not train.departed and (origin.dep_platform_confirmed or origin.dep_platform_has_changed)):
                        if dt > origin.scheduled_dep_datetime:
                            delay = f'{RED}Non partito{RESET}'
                        else:
                            delay = f'Non partito'

                # Arrival platform relative to the selected station
                if stop.arr_platform_has_changed:
                    arr_platform = f'{MAGENTA}{
                        stop.actual_arr_platform}{RESET}'
                else:
                    if stop.arr_platform_confirmed:
                        arr_platform = f'{
                            BLUE}{stop.actual_arr_platform}{RESET}'
                    else:
                        arr_platform = stop.actual_arr_platform

                table.add_row([train,
                               train.provenance,
                               train.arr_time.strftime('%H:%M'),
                               delay,
                               arr_platform])

            print(table)

    def show_journey_solutions(self, other: 'Station', dt: datetime) -> None:
        solutions = vt.travel_solutions(self.id, other.id, dt)
        print(
            f'{BOLD}Soluzioni di viaggio da {self.name} a {other.name}{RESET}')
        for sol in solutions['soluzioni']:
            # TODO: create a proper Duration and calculate the total duration since the one in the response may be wrong
            # total_duration = solution['durata'].lstrip('0').replace(':', 'h')
            vehicles = sol['vehicles']
            for vehicle in vehicles:
                # Note: this field is empty in andamentoTreno, while
                # 'categoria' isn't.
                # andamentoTreno has the field compNumeroTreno.
                # I have to check whether that's always true and what's
                # there when a train has multiple numbers
                category = vehicle['categoriaDescrizione']
                number = vehicle['numeroTreno']
                dep_time_dt = datetime.fromisoformat(vehicle['orarioPartenza'])
                arr_time_dt = datetime.fromisoformat(vehicle['orarioArrivo'])
                dep_time = dep_time_dt.strftime('%H:%M')
                arr_time = arr_time_dt.strftime('%H:%M')

                duration = Duration(arr_time_dt - dep_time_dt)

                print(
                    f'{dep_time}–{arr_time} ({category}{" " if category else ""}{number}) [{duration}]')

                # Print a train change if present
                if vehicle is not vehicles[-1]:
                    next_vehicle = vehicles[vehicles.index(vehicle) + 1]
                    vehicle_arr_time = datetime.fromisoformat(
                        vehicle['orarioArrivo'])
                    next_vehicle_dep_time = datetime.fromisoformat(
                        next_vehicle['orarioPartenza'])
                    change = Duration(next_vehicle_dep_time - vehicle_arr_time)
                    print(f'Cambio a {vehicle["destinazione"]} [{change}]')
            print()


class Stats:
    def __init__(self) -> None:
        data = vt.statistics()
        self.trains_today: int = data['treniGiorno']
        self.trains_now: int = data['treniCircolanti']
        self.last_update: datetime = datetime.fromtimestamp(
            data['ultimoAggiornamento'] / 1000).replace(tzinfo=CET)

    def __str__(self) -> str:
        return (
            f'Numero treni in circolazione da mezzanotte: {
                self.trains_today}\n'
            f'Numero treni in circolazione ora: {self.trains_now}\n'
            f'{DIM}Ultimo aggiornamento: {self.last_update.astimezone().strftime("%T")}{
                RESET}'
        )


if __name__ == '__main__':
    ap = ArgumentParser(description='Get information about trains in Italy')

    ap.add_argument('-v', '--version', action='version',
                    version=f'%(prog)s {__version__}')
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

    ap.epilog = (
        'Departures and arrivals show trains from/to'
        'the selected station in a range from 15 minutes before'
        'to 90 minutes after the selected time.'
    )

    args = ap.parse_args()

    # Check if the log level is validf
    if args.log_level not in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
        print(
            f'Invalid log level: {RED}{args.log_level}{RESET} '
            '(valid values are: DEBUG, INFO, WARNING, ERROR, CRITICAL).'
        )

        exit(1)

    logging.basicConfig(level=args.log_level)

    if args.stats:
        print(Stats())

    if args.date:
        date_ = datetime.strptime(args.date, '%Y-%m-%d').astimezone().date()
    else:
        date_ = datetime.now(UTC).date()

    if args.time:
        time_ = datetime.strptime(args.time, '%H:%M').astimezone().timetz()
    else:
        time_ = datetime.now(UTC).timetz()

    datetime_ = datetime.combine(date_, time_)

    if args.departures:
        station = Station(args.departures)
        station.show_departures(datetime_)

    if args.arrivals:
        station = Station(args.arrivals)
        station.show_arrivals(datetime_)

    if args.solutions:
        dep_station = Station(args.solutions[0])
        arr_station = Station(args.solutions[1])
        dep_station.show_journey_solutions(arr_station, datetime_)
