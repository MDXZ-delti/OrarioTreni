__version__ = "0.1"
__author__ = "Matteo Delton"

import logging
from argparse import ArgumentParser, BooleanOptionalAction
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import inquirer
from ansicolors import Foreground as F
from ansicolors import Style as S
from prettytable import PrettyTable
from viaggiatreno import ViaggiaTrenoAPIWrapper as API


class Train:
    def __init__(self, departure_station, train_number, departure_date):
        self.departure_station = departure_station
        self.train_number = train_number
        self.departure_date = departure_date

    def __str__(self):
        numbers = str(self.train_number)
        if self.number_changes:
            numbers += "/"
            numbers += "/".join(c["new_train_number"] for c in self.number_changes)

        if self.category:
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

    guesses = [(s["name"], s["id"]) for s in s]
    choice = inquirer.list_input(message="Seleziona la stazione", choices=guesses)

    name = next(s[0] for s in guesses if s[1] == choice)
    id = choice

    return name, id


def _get_track(actual_track, scheduled_track, probable_track=None):
    if actual_track is not None:
        if scheduled_track is not None:
            if actual_track == scheduled_track:
                return F.blue(actual_track)
            else:
                return F.magenta(actual_track)
        else:
            # I know it's reduntant, but I want to be explicit
            return F.blue(actual_track)

    if probable_track is not None:
        return F.blue(probable_track)

    if scheduled_track is not None:
        return scheduled_track

    return ""


def _get_delay(delay, departed_from_origin, actual_departure_track_known=False):
    if departed_from_origin:
        if delay > 0:
            return F.red(f"{delay:+}")
        elif delay < 0:
            return F.green(f"{delay:+}")
        else:
            return "In orario"
    elif actual_departure_track_known:
        return "In stazione"
    else:
        return "Non partito"


def _process_train(t, station_id, is_departure):
    train = Train(t["origin_id"], t["number"], t["departure_date"])
    train.category = t["category"]

    delay = _get_delay(t["delay"], t["departed_from_origin"])
    track = _get_track(t["actual_track"], t["scheduled_track"])

    if is_departure:
        dest_or_origin = t["destination"]
        time = t["departure_time"]
    else:
        dest_or_origin = t["origin"]
        time = t["arrival_time"]

    # Update with more accurate data
    progress = API.get_train_progress(t["origin_id"], t["number"], t["departure_date"])

    train.number_changes = progress["train_number_changes"] if progress else None

    # ViaggiaTreno is not providing real-time updates
    if not progress:
        res = [train, dest_or_origin, time.strftime("%H:%M"), delay, track]
        for i, r in enumerate(res):
            res[i] = F.yellow(r)
        return res

    departure = None
    stop = None
    arrival = None

    for s in progress["stops"]:
        if s["stop_type"] == "P":
            departure = s

        if s["station_id"] == station_id:
            stop = s

        if s["stop_type"] == "A":
            arrival = s

    # It happens e.g. with train 2965 Saronno -> Milano Centrale
    if not departure:
        departure = progress["stops"][0]

    if not arrival:
        arrival = progress["stops"][-1]

    delay = _get_delay(
        t["delay"],
        t["departed_from_origin"],
        departure["actual_departure_track"] is not None,
    )

    if is_departure:
        track = _get_track(
            stop["actual_departure_track"],
            stop["scheduled_departure_track"],
            stop["actual_arrival_track"],
        )
    else:
        track = _get_track(
            stop["actual_arrival_track"], stop["scheduled_arrival_track"]
        )

    arrived = stop["actual_arrival_time"] is not None
    departed = stop["actual_departure_time"] is not None

    res = [train, dest_or_origin, time.strftime("%H:%M"), delay, track]

    if arrived and (departed or arrival["actual_arrival_time"]):
        for i, r in enumerate(res):
            if i == 0:
                continue
            res[i] = S.dim(r)
    elif arrived and not departed:
        for i, r in enumerate(res):
            if i == 0:
                continue
            res[i] = S.bold(r)

    return res


def show_departures(station_name, station_id, dt, limit):
    print(S.bold(f"Partenze da {station_name}"))

    departures = API.get_departures(station_id, dt, limit)
    if not departures:
        print("Nessun treno in partenza nei prossimi 90 minuti.")
        return

    table = PrettyTable()
    table.field_names = ["Treno", "Destinazione", "Partenza", "Ritardo", "Binario"]

    choices = []
    with ThreadPoolExecutor(max_workers=len(departures)) as executor:
        futures = [
            executor.submit(_process_train, t, station_id, True) for t in departures
        ]

        for future in futures:
            t = future.result()
            table.add_row(t)
            choices.append((str(t[0]), t[0]))

    print(table)

    choice = inquirer.list_input(message="Seleziona un treno", choices=choices)
    show_progress(choice)


def show_arrivals(station_name, station_id, dt, limit):
    print(S.bold(f"Arrivi a {station_name}"))

    arrivals = API.get_arrivals(station_id, dt, limit)
    if not arrivals:
        print("Nessun treno in arrivo nei prossimi 90 minuti.")
        return

    table = PrettyTable()
    table.field_names = ["Treno", "Provenienza", "Arrivo", "Ritardo", "Binario"]

    with ThreadPoolExecutor(max_workers=len(arrivals)) as executor:
        futures = [
            executor.submit(_process_train, t, station_id, False) for t in arrivals
        ]

        for future in futures:
            t = future.result()
            table.add_row(t)

    print(table)


def show_progress(train):
    p = API.get_train_progress(
        train.departure_station, train.train_number, train.departure_date
    )

    if not p:
        print(
            "ViaggiaTreno non sta fornendo aggiornamenti in tempo reale per questo treno."
        )
        return

    print(
        f"Treno {train} · {_get_delay(p['delay'], p['stops'][0]['actual_departure_time'] is not None, p['stops'][0]['actual_departure_track'] is not None)}\n"
        f"{p['departure_time'].strftime('%H:%M')} {p['origin']}\n"
        f"{p['arrival_time'].strftime('%H:%M')} {p['destination']}"
    )

    if p["last_update_station"] and p["last_update_time"]:
        print(
            f"\nUltimo aggiornamento: {p['last_update_time'].strftime('%H:%M')} a {p['last_update_station']}"
        )

    for s in p["stops"]:
        track = _get_track(
            s["actual_departure_track"] or s["actual_arrival_track"],
            s["scheduled_departure_track"] or s["scheduled_arrival_track"],
        )

        if track:
            print(f"\n{s['station_name']} · {track}")
        else:
            print(f"\n{s['station_name']}")

        if s["stop_type"] in ("A", "F"):
            if actual_arrival_time := s["actual_arrival_time"]:
                if actual_arrival_time > s["scheduled_arrival_time"]:
                    actual_arrival_time = F.red(actual_arrival_time.strftime("%H:%M"))
                else:
                    actual_arrival_time = F.green(actual_arrival_time.strftime("%H:%M"))
            arr_str = f"Arr.:\t{s['scheduled_arrival_time'].strftime('%H:%M')}"
            if actual_arrival_time:
                arr_str += f"\t{actual_arrival_time}"
            else:
                if not s["actual_departure_time"]:
                    arr_str += F.yellow(
                        f"\t{(s['scheduled_arrival_time'] + timedelta(minutes=p['delay'])).strftime('%H:%M')}"
                    )
            print(arr_str)

        if s["stop_type"] in ("P", "F"):
            if actual_departure_time := s["actual_departure_time"]:
                if actual_departure_time > s["scheduled_departure_time"] + timedelta(
                    seconds=30
                ):
                    actual_departure_time = F.red(
                        actual_departure_time.strftime("%H:%M")
                    )
                else:
                    actual_departure_time = F.green(
                        actual_departure_time.strftime("%H:%M")
                    )
            dep_str = f"Dep.:\t{s['scheduled_departure_time'].strftime('%H:%M')}"
            if actual_departure_time:
                dep_str += f"\t{actual_departure_time}"
            else:
                if not s["actual_arrival_time"]:
                    dep_str += F.yellow(
                        f"\t{(s['scheduled_departure_time'] + timedelta(minutes=p['delay'])).strftime('%H:%M')}"
                    )
            print(dep_str)


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
        help="show departures from STATION",
    )
    ap.add_argument(
        "-a",
        "--arrivals",
        metavar="STATION",
        type=str,
        help="show arrivals to STATION",
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
        help="show/don't show statistics about trains (defaults to True)",
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
        "Departures and arrivals show trains from/to the selected "
        "station in a range from 15 minutes before to 90 minutes after "
        "the selected time."
    )

    args = ap.parse_args()

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
        station_name, station_id = choose_station(args.arrivals)
        show_arrivals(station_name, station_id, dt, limit)

    if args.solutions:
        print("Not implemented yet")
        pass
