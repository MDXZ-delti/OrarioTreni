__version__ = "0.1"
__author__ = "Matteo Delton"

import logging
from argparse import ArgumentParser, BooleanOptionalAction
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import inquirer
from prettytable import PrettyTable

from ansicolors import Foreground as F
from ansicolors import Style as S
from viaggiatreno import ViaggiaTrenoAPIWrapper as API


class Train:
    def __init__(self, departure_station, train_number, departure_date):
        self.departure_station = departure_station
        self.train_number = train_number
        self.departure_date = departure_date

    def __str__(self):
        numbers = self.train_number
        if hasattr(self, "number_changes"):
            numbers += "/".join(c["new_train_number"] for c in self.number_changes)

        if hasattr(self, "category"):
            return f"{self.category} {numbers}"
        else:
            return f"{numbers}"

    def __repr__(self):
        return f"Train({self.departure_station}, {self.train_number}, {self.departure_date})"


def show_statistics():
    s = API.get_statistics()

    print(
        f"Treni in circolazione da mezzanotte: {s['trains_since_midnight']}\n"
        f"Treni in circolazione ora: {s['trains_running']}\n"
        f"{S.DIM}Ultimo aggiornamento: {s['last_update'].strftime('%T')}{S.NORMAL}"
    )


def choose_station(station):
    s = API.get_stations_matching_prefix(station)

    if not s:
        print("Nessuna stazione trovata")
        return

    if len(s) == 1:
        return s[0]["name"], s[0]["id"]

    guesses = tuple((s["name"], s["id"]) for s in s)
    choice = inquirer.list_input(message="Seleziona la stazione", choices=guesses)

    name = next(s[0] for s in guesses if s[1] == choice)
    id = choice

    return name, id


def _process_train(t):
    train = Train(t["origin_id"], t["number"], t["departure_date"])
    train.category = t["category"]

    if t["departed_from_origin"]:
        if t["delay"] > 0:
            delay = F.red(f'{t["delay"]:+}')
        elif t["delay"] < 0:
            delay = F.green(f'{t["delay"]:+}')
        else:
            delay = "In orario"
    else:
        delay = "Non partito"

    if t["track"] is None:
        track = t["scheduled_track"] or ""
    elif t["track"] == t["scheduled_track"]:
        track = F.blue(t["track"])
    else:
        # Even if scheduled track is None…
        track = F.magenta(t["track"])

    # Update with more accurate data
    tp = API.get_train_progress(t["origin_id"], t["number"], t["departure_date"])

    if tp:
        train.number_changes = tp["train_number_changes"]

        s = None
        o = None
        for stop in tp["stops"]:
            if stop["station_id"] == station_id and s is None:
                s = stop
            if stop["station_id"] == t["origin_id"] and o is None:
                o = stop
            if s is not None and o is not None:
                break

        assert s is not None and o is not None

        if t["departed_from_origin"]:
            if tp["delay"] > 0:
                delay = F.red(f'{tp["delay"]:+}')
            elif tp["delay"] < 0:
                delay = F.green(f'{tp["delay"]:+}')
            else:
                delay = "In orario"
        elif s["departure_track"]:
            delay = "In stazione"  # Pronto a sfrecciare
        elif o["departure_track"]:
            delay = "In stazione"  # Quella di origine
        else:
            delay = "Non partito"  # E non si sa dov'è

        if s["departure_track"] is None:
            # Assuming that the trains departs from the same track
            if s["arrival_track"] is not None:
                if s["arrival_track"] == s["scheduled_arrival_track"]:
                    track = F.blue(s["arrival_track"])
                else:
                    track = F.magenta(s["arrival_track"])
            else:
                if s["scheduled_departure_track"] is not None:
                    track = s["scheduled_departure_track"]
                else:
                    # Not enough data
                    track = ""
        elif s["departure_track"] == s["scheduled_departure_track"]:
            track = F.blue(s["departure_track"])
        else:
            # Even if scheduled track is None…
            track = F.magenta(s["departure_track"])

    res = [train, t["destination"], t["departure_time"].strftime("%H:%M"), delay, track]

    # Dim the row if the train has already left the station
    if t["departed_from_station"]:
        for i, r in enumerate(res):
            res[i] = S.dim(r)

    # ViaggiaTreno is not providing real-time updates
    if not tp:
        for i, r in enumerate(res):
            res[i] = F.yellow(r)

    return res


def show_departures(station_name, station_id, dt, limit):
    print(S.bold(f"Partenze da {station_name}"))

    departing_trains = API.get_departures(station_id, dt, limit)
    if not departing_trains:
        print("Nessun treno in partenza nei prossimi 90 minuti.")
        return

    table = PrettyTable()
    table.field_names = ["Treno", "Destinazione", "Partenza", "Ritardo", "Binario"]

    with ThreadPoolExecutor(max_workers=len(departing_trains)) as executor:
        for t in executor.map(_process_train, departing_trains):
            table.add_row(t)

    print(table)


if __name__ == "__main__":
    ap = ArgumentParser(description="Get information about trains in Italy")

    ap.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    ap.add_argument(
        "-d",
        "--departures",
        metavar="STATION",
        type=str,
        help="show departures from a station",
    )
    ap.add_argument(
        "-a",
        "--arrivals",
        metavar="STATION",
        type=str,
        help="show arrivals to a station",
    )
    ap.add_argument(
        "-s",
        "--solutions",
        metavar=("DEPARTURE", "ARRIVAL"),
        type=str,
        nargs=2,
        help="show journey solutions from DEPARTURE to ARRIVAL",
    )
    ap.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        type=str,
        help="date to use for the other actions (defaults to today)",
    )
    ap.add_argument(
        "--time",
        metavar="HH:MM",
        type=str,
        help="time to use for the other actions (defaults to now)",
    )
    ap.add_argument(
        "--limit",
        metavar="N",
        type=int,
        help="limit the number of results to N (defaults to 10)",
        default=10,
    )
    ap.add_argument(
        "--stats",
        action=BooleanOptionalAction,
        help="show/don't show stats (defaults to True)",
        default=True,
    )
    ap.add_argument(
        "--log-level",
        metavar="LEVEL",
        type=str,
        help="set the logging level (defaults to WARNING)",
        default="WARNING",
    )

    ap.epilog = (
        "Departures and arrivals show trains from/to"
        "the selected station in a range from 15 minutes before"
        "to 90 minutes after the selected time."
    )

    args = ap.parse_args()

    # Check if the log level is validf
    if args.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        print(
            f"Invalid log level: {F.red(args.log_level)} "
            "(valid values are: DEBUG, INFO, WARNING, ERROR, CRITICAL)."
        )

        exit(1)

    logging.basicConfig(level=args.log_level)

    if args.stats:
        show_statistics()

    if args.date:
        date_ = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        date_ = datetime.now().date()

    if args.time:
        time_ = datetime.strptime(args.time, "%H:%M").time()
    else:
        time_ = datetime.now().time()

    if args.limit:
        limit = args.limit

    dt = datetime.combine(date_, time_)

    if args.departures:
        station_name, station_id = choose_station(args.departures)
        show_departures(station_name, station_id, dt, limit)

    if args.arrivals:
        pass

    if args.solutions:
        pass
