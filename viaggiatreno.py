import json
import logging
from csv import DictWriter
from datetime import UTC, date, datetime, time
from pathlib import Path

import requests


class ViaggiaTreno:
    """A wrapper for the ViaggiaTreno API."""

    BASE_URL: str = 'http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno'
    REGIONS: dict[int, str] = {
        0: 'Italia',
        1: 'Lombardia',
        2: 'Liguria',
        3: 'Piemonte',
        4: 'Valle d\'Aosta',
        5: 'Lazio',
        6: 'Umbria',
        7: 'Molise',
        8: 'Emilia Romagna',
        9: 'Trentino-Alto Adige',
        10: 'Friuli-Venezia Giulia',
        11: 'Marche',
        12: 'Veneto',
        13: 'Toscana',
        14: 'Sicilia',
        15: 'Basilicata',
        16: 'Puglia',
        17: 'Calabria',
        18: 'Campania',
        19: 'Abruzzo',
        20: 'Sardegna',
        21: 'Provincia autonoma di Treno',
        22: 'Provincia autonoma di Bolzano'
    }

    def _get(self, method: str, *params):
        """call the ViaggiaTreno API with the given method and parameters."""

        url = f'{self.BASE_URL}/{method}/{"/".join(str(p) for p in params)}'

        r = requests.get(url)

        if r.status_code != 200:
            logging.error(f'Error {r.status_code} while calling {
                          url}: {r.text}')
            return None

        if (logging.getLogger().getEffectiveLevel() == logging.DEBUG):
            dt = datetime.strptime(
                r.headers['Date'], '%a, %d %b %Y %H:%M:%S %Z').strftime('%Y-%j %X')
            filename = f'{dt} {method}({", ".join(str(p) for p in params)})'
            Path('responses').mkdir(parents=True, exist_ok=True)
            with open(f'responses/{filename}.json', 'w') as f:
                json.dump(r.json(), f, indent=2)
                f.write('\n')

        return r.json() if 'json' in r.headers['Content-Type'] else r.text

    def departures(self, codiceStazione: str, dt: datetime):
        """Return the departures from the given station at the given time.
        If the time is naive, it is assumed to be in the local timezone.
        """

        # Maybe time zones are not needed at all, or they CAN be read
        # but are not required (in that case, the API would assume the
        # Rome time zone)
        if dt.tzinfo is None:
            dt = dt.astimezone()

        dep_time = dt.strftime('%a %b %d %Y %H:%M:%S UTC%z')

        return self._get('partenze', codiceStazione, dep_time)

    def arrivals(self, codiceStazione: str, dt: datetime):
        """Return the arrivals from the given station at the given time.
        If the time is naive, it is assumed to be in the local timezone.
        """

        # Maybe time zones are not needed at all, or they CAN be read
        # but are not required (in that case, the API would assume the
        # Rome time zone). The API accepts the name of the time zone
        # (e.g. Central European Time) in parentheses, at the end of
        # the string, but it seems to ignore it.
        if dt.tzinfo is None:
            dt = dt.astimezone()

        arr_time = dt.strftime('%a %b %d %Y %H:%M:%S UTC%z')

        return self._get('arrivi', codiceStazione, arr_time)

    def tratte_canvas(self, codiceOrigine, numeroTreno, dataPartenza):
        pass
        return self._get('tratteCanvas', codiceOrigine, numeroTreno, dataPartenza)

    def cerca_numero_treno_treno_auto_complete(self, text):
        pass
        return self._get('cercaNumeroTrenoTrenoAutocomplete', text)

    # TODO: check if it returns None or an empty string when no match is found
    def autocompleta_stazione(self, text: str) -> str:
        return self._get('autocompletaStazione', text)

    def language(self, idLingua):
        pass
        return self._get('language', idLingua)

    def travel_solutions(self, origin_id: str, dest_id: str, dt: datetime):
        """Return travel solutions from the given origin to the given
        destination at the given time.
        If the time is naive, it is assumed to be in the local timezone.
        The station codes can either be the ones retuned by the API
        (which start with a letter and are followed by the actual
        station code padded with zeroes up to 5 digits) or the actual
        station code (which is a number).
        """

        origin_id = origin_id.lstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ0')
        dest_id = dest_id.lstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ0')

        search_datetime: str = dt.isoformat()

        return self._get('soluzioniViaggioNew', origin_id, dest_id, search_datetime)

    def elenco_stazioni_citta(self, stazione: str):
        pass
        return self._get('elencoStazioniCitta', stazione)

    def wheather(self, region_code: int):
        # I'm not sure about what the API return when the region code is
        # 0, the codes are different than the ones found in the regions
        pass
        return self._get('datiMeteo', region_code)

    def dettaglio_stazione(self, codiceStazione, codiceRegione: int):
        pass
        return self._get('dettaglioStazione', codiceStazione, codiceRegione)

    def stations_list(self, region_code: int):
        return self._get('elencoStazioni', region_code)

    def autocompleta_stazione_imposta_viaggio(self, text: str):
        pass
        return self._get('autocompletaStazioneImpostaViaggio', text)

    def autocompleta_stazione_nts(self, text: str):
        pass
        return self._get('autocompletaStazioneNTS', text)

    def property(self, name):
        pass
        return self._get('property', name)

    def infomobilita_rss_box(self, isInfoLavori):
        pass
        return self._get('infomobilitaRSSBox', isInfoLavori)

    def train_status(self, origin_id: str, train_number: int, dep_date: date | datetime | int | str):
        """Return the status of the given train at the given time.
        The origin id is the one returned by the API (which starts with
        a letter and is followed by the actual station code padded with
        zeroes up to 5 digits).
        """
        search = Utils.to_ms_date_timestamp(dep_date)
        return self._get('andamentoTreno', origin_id, train_number, search)

    def cerca_numero_treno(self, numeroTreno):
        pass
        return self._get('cercaNumeroTreno', numeroTreno)

    def infomobilita_ticker(self):
        pass
        return self._get('infomobilitaTicker')

    def elenco_tratte(self, idRegione, zoomlevel, categoriaTreni, catAV, timestamp):
        pass
        return self._get('elencoTratte', idRegione, zoomlevel, categoriaTreni, catAV, timestamp)

    def cerca_programma_orario_destinazione_autocomplete(self, idStazionePartenza):
        pass
        return self._get('cercaProgrammaOrarioDestinazioneAutocomplete', idStazionePartenza)

    def dettaglio_viaggio(self, idStazioneDa, idStazioneA):
        pass
        return self._get('dettaglioViaggio', idStazioneDa, idStazioneA)

    def dettaglio_programma_orario(self, dataDa, dataA, idStazionePartenza, idStazioneArrivo):
        pass
        return self._get('dettaglioProgrammaOrario', dataDa, dataA, idStazionePartenza, idStazioneArrivo)

    def statistics(self, dt: datetime | None = None) -> dict[str, int]:
        """Return statistics about trains.
        Even though the API requires a timestamp, it seems to ignore it and
        returns the same data regardless of the timestamp. Therefore, the
        timestamp is not required and defaults to the current time.
        """
        if dt is None:
            dt = datetime.now(UTC)

        timestamp = int(dt.timestamp() * 1000)

        return self._get('statistiche', timestamp)

    def find_station(self, text: str):
        return self._get('cercaStazione', text)

    def region(self, codiceStazione: str) -> int | None:
        return self._get('regione', codiceStazione)

    def cerca_programma_orario_origine_autocomplete(self, idStazioneArrivo):
        pass
        return self._get('cercaProgrammaOrarioOrigineAutocomplete', idStazioneArrivo)

    def dettagli_tratta(self, idRegione, idTrattaAB, idTrattaBA, categoriaTreni, catAV):
        pass
        return self._get('dettagliTratta', idRegione, idTrattaAB, idTrattaBA, categoriaTreni, catAV)

    def infomobilita_rss(self, isInfoLavori):
        pass
        return self._get('infomobilitaRSS', isInfoLavori)


class Utils:
    vt = ViaggiaTreno()

    @classmethod
    def generate_station_database(cls):
        with open('stations.csv', 'w', newline='') as csvfile:
            fieldnames = ['short_name', 'region_code', 'station_id',
                          'long_name', 'label', 'lat', 'lon', 'station_type']
            writer = DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for n in range(23):
                stations = cls.vt.stations_list(n)
                for s in stations:
                    writer.writerow({
                        'short_name': s['localita']['nomeBreve'],
                        'region_code': s['codReg'],
                        'station_id': s['codStazione'],
                        'long_name': s['localita']['nomeLungo'],
                        'label': s['localita']['label'],
                        'lat': s['lat'],
                        'lon': s['lon'],
                        'station_type': s['tipoStazione']
                    })

            # TODO: remove duplicates before writing to file

    @classmethod
    def to_ms_date_timestamp(cls, date_: date | datetime | int | str) -> int:
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
            dt = datetime.combine(dt.date(), time.min)

        return int(dt.timestamp() * 1000)  # Milliseconds instead of seconds
