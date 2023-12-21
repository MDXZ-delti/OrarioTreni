__version__ = '0.1'
__author__ = 'Matteo Delton'

from datetime import date, datetime, time

import requests


class ViaggiaTrenoAPIWrapper:
    """A wrapper for the ViaggiaTreno API.

    As a general rule, station ids required as arguments are always
    in the form a an 'S' followed by the ENEE code of the station
    padded with zeroes until it's 5 digits long. The ids returned by
    this class' methods are always in this form.

    Departure and arrival times are always datetime objects and not
    time objects because otherwise it would be impossible compute a
    correct duration in every case.

    Train numbers are strings because they can contain letters (e.g. Urb)
    """

    BASE_URI = 'http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno'

    @classmethod
    def _get(cls, endpoint, *args):
        url = f'{cls.BASE_URI}/{endpoint}/{"/".join(str(arg) for arg in args)}'
        r = requests.get(url)
        r.raise_for_status()

        print(requests.utils.requote_uri(url))

        return r.json() if 'json' in r.headers['Content-Type'] else r.text

    @classmethod
    def get_statistics(cls):
        """Return statistics about trains for today."""
        timestamp = int(datetime.now().timestamp() * 1000)
        r = cls._get('statistiche', timestamp)

        statistics = {
            'trains_since_midnight': r['treniGiorno'],
            'trains_running': r['treniCircolanti'],
            'last_update': Utils.from_ms_timestamp(r['ultimoAggiornamento'])
        }

        return statistics

    @classmethod
    def get_stations_matching_prefix(cls, prefix):
        """Return a list of stations starting with the given text."""
        r = cls._get('cercaStazione', prefix)

        stations = []
        for s in r:
            stations.append({
                'name': s['nomeLungo'],
                'id': s['id']
            })

        return stations

    @classmethod
    def get_departures(cls, station_id, dt=None, limit=10):
        """Return the departures from a station at a certain time."""
        if dt is None:
            dt = datetime.now()

        dep_time = Utils.to_string(dt)
        r = cls._get('partenze', station_id, dep_time)

        departures = []
        for i, d in enumerate(r):
            if i == limit:
                break

            departures.append({
                'category': d['categoriaDescrizione'].strip(),
                'number': d['numeroTreno'],
                'departure_date': Utils.from_ms_timestamp(d['dataPartenzaTreno']).date(),
                'origin_id': d['codOrigine'],
                'destination': d['destinazione'],
                'scheduled_track': d['binarioProgrammatoPartenzaDescrizione'],
                'track': d['binarioEffettivoPartenzaDescrizione'],
                'departure_time': Utils.from_ms_timestamp(d['orarioPartenza']),
                'departed_from_origin': not d['nonPartito'],
                'departed_from_station': d['inStazione'],
                'delay': int(d['ritardo']),
                'warning': d['subTitle']
            })

        return departures

    @classmethod
    def get_arrivals(cls, station_id, dt=None, limit=10):
        """Return the arrivals to a station at a certain time."""
        if dt is None:
            dt = datetime.now()

        arr_time = Utils.to_string(dt)
        r = cls._get('arrivi', station_id, arr_time)

        arrivals = []
        for i, a in enumerate(r):
            if i == limit:
                break

            arrivals.append({
                'category': a['categoriaDescrizione'].strip(),
                'number': a['numeroTreno'],
                'departure_date': Utils.from_ms_timestamp(a['dataPartenzaTreno']).date(),
                'origin_id': a['codOrigine'],
                'origin': a['origine'],
                'scheduled_track': a['binarioProgrammatoArrivoDescrizione'],
                'track': a['binarioEffettivoArrivoDescrizione'],
                'arrival_time': Utils.from_ms_timestamp(a['orarioArrivo']),
                'departed_from_origin': not a['nonPartito'],
                'departed_from_station': a['inStazione'],
                'delay': int(a['ritardo']),
                'warning': a['subTitle']
            })

        return arrivals

    @classmethod
    def get_train_info(cls, train_number):
        r = cls._get('cercaNumeroTreno', train_number)

        train = {
            'number': r['numeroTreno'],
            'departure_date': Utils.from_ms_timestamp(r['dataPartenza']).date(),
            'departure_station_id': r['codLocOrig'],
            'departure_station': r['descLocOrig']
        }

        return train

    @classmethod
    def get_travel_solutions(cls, origin_id, dest_id, dt=None, limit=10):
        """Return travel solutions between two stations."""
        if dt is None:
            dt = datetime.now()

        origin_id = cls._get_enee_code(origin_id)
        dest_id = cls._get_enee_code(dest_id)
        dt = dt.isoformat()
        r = cls._get('soluzioniViaggioNew', origin_id, dest_id, dt)

        solutions = {
            'origin': r['origine'],
            'destination': r['destinazione'],
            'solutions': []
        }

        for i, s in enumerate(r['soluzioni']):
            if i == limit:
                break

            vehicles = []
            for v in s['vehicles']:
                vehicles.append({
                    'origin': v['origine'],
                    'destination': v['destinazione'],
                    'departure_time': datetime.fromisoformat(v['orarioPartenza']),
                    'arrival_time': datetime.fromisoformat(v['orarioArrivo']),
                    'category': v['categoriaDescrizione'],
                    'number': v['numeroTreno']
                })

            solutions['solutions'].append({
                'vehicles': vehicles
            })

        return solutions

    @classmethod
    def get_train_progress(cls, origin_id, train_number, dep_date):
        """Return the progress of a train."""
        dep_date = Utils.to_ms_date_timestamp(dep_date)
        r = cls._get('andamentoTreno', origin_id,
                     train_number, dep_date)

        if not r:
            return None

        train_number_changes = []
        for c in r['cambiNumero']:
            train_number_changes.append({
                'new_train_number': c['nuovoNumeroTreno'],
                'station': c['stazione']
            })

        stops = []
        for s in r['fermate']:
            stops.append({
                'station_id': s['id'],
                'station': s['stazione'],
                'scheduled_arrival_time': Utils.from_ms_timestamp(s['arrivo_teorico']),
                'arrival_time': Utils.from_ms_timestamp(s['arrivoReale']),
                'scheduled_departure_time': Utils.from_ms_timestamp(s['partenza_teorica']),
                'departure_time': Utils.from_ms_timestamp(s['partenzaReale']),
                'scheduled_arrival_track': s['binarioProgrammatoArrivoDescrizione'],
                'arrival_track': s['binarioEffettivoArrivoDescrizione'],
                'scheduled_departure_track': s['binarioProgrammatoPartenzaDescrizione'],
                'departure_track': s['binarioEffettivoPartenzaDescrizione'],
            })

        # Check fermateSoppresse, tipoTreno and motivoRitardoPrevalente
        # There's a numeroTreno which is an int here
        progress = {
            'last_update': Utils.from_ms_timestamp(r['oraUltimoRilevamento']),
            'last_update_station': s if (s := r['stazioneUltimoRilevamento']) != '--' else None,
            'number': str(r['numeroTreno']),
            'departure_date': Utils.from_ms_timestamp(r['dataPartenzaTreno']).date(),
            'origin_id': r['idOrigine'],
            'origin': r['origine'],
            'destination': r['destinazione'],
            'destination_id': r['idDestinazione'],
            'train_number_changes': train_number_changes,
            'departure_time': Utils.from_ms_timestamp(r['orarioPartenza']),
            'arrival_time': Utils.from_ms_timestamp(r['orarioArrivo']),
            'departed': not r['nonPartito'],
            'in_station': r['inStazione'],
            'delay': int(r['ritardo']),
            'warning': r['subTitle'] or None,
            'delay_reason': r['motivoRitardoPrevalente'],
            'stops': stops
        }

        return progress


class Utils:
    """A collection of utility functions."""

    @classmethod
    def to_ms_date_timestamp(cls, date_):
        """Return the timestamp of the given date at midnight in
        milliseconds.

        The date can be a date, a datetime, a timestamp in milliseconds
        or a string in ISO 8601 format.
        """
        if isinstance(date_, date):
            dt = datetime.combine(date_, time.min)
        elif isinstance(date_, datetime):
            dt = datetime.combine(date_.date(), time.min)
        elif isinstance(date_, int):
            dt = datetime.fromtimestamp(date_ / 1000)
            dt = datetime.combine(dt.date(), time.min)
        elif isinstance(date_, str):
            try:
                dt = datetime.fromisoformat(date_)
            except ValueError:
                raise ValueError(f'Invalid date format: {date_}') from None

        return int(dt.timestamp() * 1000)

    @classmethod
    def to_string(cls, dt):
        if isinstance(dt, int):
            dt = datetime.fromtimestamp(dt / 1000)
        elif isinstance(dt, str):
            dt = datetime.fromisoformat(dt)

        return dt.strftime('%a %b %d %Y %H:%M:%S')

    @classmethod
    def get_enee_code(cls, station_id):
        if len(station_id) == 6:
            station_id = int(station_id.lstrip('S0'))
        elif len(station_id) == 8:
            station_id = int(station_id.lstrip('830'))

        return station_id

    # TODO: accept a datetime object as well
    @classmethod
    def from_ms_timestamp(cls, dt):
        if dt is None:
            return None

        dt = datetime.fromtimestamp(dt / 1000)

        return dt
