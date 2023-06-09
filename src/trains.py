#!/usr/bin/env python

import argparse
import datetime
from concurrent.futures import ThreadPoolExecutor

import inquirer
import prettytable

import API
import Style

# TODO:
# - Handle the case where the train does not have all the stops.
#   Saronno is a good example.
# - Test loglevel
# - Add "trip duration" field ("compDurata" in andamentoTreno)
# - Check the field "nonPartito" under partenze
# - "binarioProgrammatoPartenzaCodice": "0" MAY mean that a train is in the station

datetime.UTC = datetime.timezone.utc


class Train:
    def __init__(self, data):
        # TODO: check with the departure time (?)
        self.departed = data['inStazione']
        self.departure_date = data['dataPartenzaTreno']
        self.departure_time = data['compOrarioPartenza']
        self.origin_station = Station(
            None, data['codOrigine'] or data['idOrigine'])
        self.destination = data['destinazione']
        self.category = data['categoriaDescrizione'].strip()
        self.number = data['numeroTreno']


# Maybe this should inherit from Train.
# I have to check the JSONs returned by the API
class Journey:
    def __init__(self, origin_station, train_number, departure_date):
        data = getJourneyInfo(origin_station, train_number, departure_date)

        if (not data):
            raise Exception('Trenitalia non sta fornendo aggiornamenti')

        self.last_update_time = data['oraUltimoRilevamento']
        self.last_update_station = data['stazioneUltimoRilevamento']

        # 'ritardo' is the departure delay if the station is the
        # first of the journey, otherwise it's the arrival delay
        self.delay = data['ritardo']

        self.train_numbers = train_number
        if (data['haCambiNumero']):
            for change in data['cambiNumero']:
                self.train_numbers += '/' + change['nuovoNumeroTreno']

        self.stops = [Stop(stop) for stop in data['fermate']]

    @classmethod
    def fromTrain(cls, train: Train):
        return cls(train.origin_station, train.number, train.departure_date)

    def __str__(self) -> str:
        return f'Dettagli del treno {self.train_number} con partenza da {self.origin_station} in data {self.departure_date}'


# This should inherit from Station.
# I could then call getDepartures or something from a Stop
class Stop:
    """Stop in a journey.

    Part of the response of the API.andamentoTreno() method carrying information about the platform, the delay, and the arrival/departure time.
    """

    def __init__(self, data):
        self.id = data['id']
        self.name = data['stazione']
        # Note: some of the data about the platform might be available under partenze
        self.scheduled_departure_platform = data['binarioProgrammatoPartenzaDescrizione']
        self.actual_departure_platform = data['binarioEffettivoPartenzaDescrizione']
        self.scheduled_arrival_platform = data['binarioProgrammatoArrivoDescrizione']
        self.actual_arrival_platform = data['binarioEffettivoArrivoDescrizione']
        self.departure_delay = data['ritardoPartenza']
        self.arrival_delay = data['ritardoArrivo']
        self.delay = data['ritardo']
        self.scheduled_departure_time = data['partenza_teorica']
        self.actual_departure_time = data['partenzaReale']
        self.scheduled_arrival_time = data['arrivo_teorico']
        self.actual_arrival_time = data['arrivoReale']

    def departurePlatformHasChanged(self) -> bool:
        return self.actual_departure_platform and self.actual_departure_platform != self.scheduled_departure_platform

    def getDeparturePlatform(self) -> str:
        """Get the actual departure platform if it's available, otherwise the scheduled one."""
        return self.actual_departure_platform if self.departurePlatformHasChanged() else self.scheduled_departure_platform


class Station:
    def __init__(self, name=None, id=None):
        self.name = name
        self.id = id

        if (name is None and id is None):
            name = inquirer.text('Inserisci il nome della stazione')

        if (id is None):
            r = API.cercaStazione(name)

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
            date = datetime.datetime.now(datetime.UTC)
        if isinstance(date, int):
            date = datetime.datetime.fromtimestamp(date)
        if isinstance(date, datetime.datetime):
            date = date.strftime('%a %b %d %Y %H:%M:%S GMT%z (%Z)')
        return API.partenze(self.id, date)

    def getArrivals(self, date=None):
        if (date is None):
            date = datetime.datetime.now(datetime.UTC)
        if isinstance(date, int):
            date = datetime.datetime.fromtimestamp(date)
        if isinstance(date, datetime.datetime):
            date = date.strftime('%a %b %d %Y %H:%M:%S GMT%z (%Z)')
        return API.arrivi(self.id, date)

    def getJourneySolutions(self, other, time=None):
        codLocOrig = self.id[1:]
        codLocDest = other.id[1:]
        if (time is None):
            time = datetime.datetime.now(datetime.UTC)
        if isinstance(time, int):
            time = datetime.datetime.fromtimestamp(time)
        if isinstance(time, datetime.datetime):
            time = time.strftime('%FT%T')
        return API.soluzioniViaggioNew(codLocOrig, codLocDest, time)

    def showDepartures(self, date=None) -> None:
        """Prints the departures from the station.

        Gets the actual delay and platform by querying the API (andamentoTreno) for each train.
        """
        departures = [Train(d) for d in self.getDepartures(date)]
        print(f'{Style.BOLD}Partenze da {self.name}{Style.RESET}')

        table = prettytable.PrettyTable()
        table.field_names = ['Treno', 'Destinazione',
                             'Partenza', 'Ritardo', 'Binario']

        if (len(departures) == 0):
            print('Nessun treno in partenza')
            return

        with ThreadPoolExecutor(len(departures)) as pool:
            futures = pool.map(Journey.fromTrain, departures)
            for (train, journey) in zip(departures, futures, strict=True):
                # Number changes are returned by API.andamentoTreno()
                # API.partenze() only says if the train has changed number
                train.numbers = journey.train_numbers

                # Get info relative to the selected station
                stop = next(s for s in journey.stops if s.id == self.id)

                # Departure platform relative to the selected station
                train.departure_platform = stop.getDeparturePlatform()

                # Try to get the delay from the stop.
                # If it's not available, use the one from the journey
                delay = stop.delay or journey.delay
                delay_text = f'{Style.RED if delay > 0 else Style.GREEN}{delay:+} min{Style.RESET}' if delay else ''

                table.add_row([f'{train.category} {train.number}',
                               train.destination,
                               train.departure_time,
                               delay_text,
                               train.departure_platform or ''])

            table.set_style(prettytable.SINGLE_BORDER)
            print(table)

    # TODO: implement
    def showArrivals(self, date=None):
        print('To be implemented')

    # TODO: adjust the code
    def showJourneySolutions(self, other, time=None):
        print('To be implemented, this is a stub')
        solutions = self.getJourneySolutions(other, time)
        print(
            f'{Style.BOLD}Soluzioni di viaggio da {self.name} a {other.name}{Style.RESET}')
        for solution in solutions['soluzioni']:
            duration = f'{str(solution["durata"]).replace(":", "h")} min'
            sols = []
            for vehicle in solution['vehicles']:
                # Note: this field is empty in andamentoTreno, while "categoria" isn't
                # andamentoTreno has the filed compNumeroTreno. I have to check whether that's always true and what's there when a train has multiple numbers
                category = vehicle['categoriaDescrizione']
                number = vehicle['numeroTreno']
                departure_time = datetime.datetime.fromisoformat(
                    vehicle['orarioPartenza']).strftime('%H:%M')
                arrival_time = datetime.datetime.fromisoformat(
                    vehicle['orarioArrivo']).strftime('%H:%M')

                print(
                    f'{departure_time}–{arrival_time} ({category}{" " if category else ""}{number})')

                # Print a train change if present
                if (len(solutions['soluzioni']) > 1 and vehicle is not solution['vehicles'][-1]):
                    oa = datetime.datetime.fromisoformat(
                        vehicle['orarioArrivo'])
                    next_vehicle = solution['vehicles'][solution['vehicles'].index(
                        vehicle) + 1]
                    od = datetime.datetime.fromisoformat(
                        next_vehicle['orarioPartenza'])
                    change = int((od - oa).total_seconds() / 60)
                    print(
                        f'Cambio a {vehicle["destinazione"]} di {change} min')
            print()


def getStats(timestamp):
    """Query the endpoint <statistiche>."""
    if (timestamp is None):
        timestamp = datetime.datetime.now(datetime.UTC)
    if (isinstance(timestamp, datetime.datetime)):
        timestamp = int(timestamp.timestamp() * 1000)
    return API.statistiche(timestamp)


def showStats():
    """Show national statistics about trains."""
    now = datetime.datetime.now(datetime.UTC)
    r = API.statistiche(now)
    print(f'Numero treni in circolazione da mezzanotte: {r["treniGiorno"]}')
    print(f'Numero treni in circolazione ora: {r["treniCircolanti"]}')
    print(f'{Style.DIM}Ultimo aggiornamento: {now.astimezone().strftime("%T")}\n{Style.RESET}')


def getJourneyInfo(departure_station, train_number, departure_date):
    """Query the endpoint <andamentoTreno>."""
    return API.andamentoTreno(departure_station.id,
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
