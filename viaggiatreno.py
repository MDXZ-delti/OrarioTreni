from datetime import date, datetime, time
from typing import Any

import requests

type JSON = Any
type HTML = str


class ViaggiaTreno:
    """A wrapper for the ViaggiaTreno API."""

    BASE_URI: str = 'http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno'
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

    # TODO: add optional parameters date and time. They'll need to be
    # combined. If one of them is missing, it should default to the
    # current date/time. Make dt optional.
    def departures(self, station_id: str, dt: datetime) -> JSON:
        """Return the departures from the given station at the given time.
        If the time is naive, it is assumed to be in the local timezone.
        """
        dep_time = dt.strftime('%a %b %d %Y %H:%M:%S')

        url: str = f'{
            self.BASE_URI}/partenze/{station_id}/{dep_time}'
        r = requests.get(url)

        return r.json()

    # TODO: add optional parameters date and time. They'll need to be
    # combined. If one of them is missing, it should default to the
    # current date/time. Make dt optional.
    def arrivals(self, station_id: str, dt: datetime) -> JSON:
        """Return the arrivals from the given station at the given time.
        If the time is naive, it is assumed to be in the local timezone.
        """
        arr_time = dt.strftime('%a %b %d %Y %H:%M:%S')

        url: str = f'{
            self.BASE_URI}/arrivi/{station_id}/{arr_time}'
        r = requests.get(url)

        return r.json()

    def tratte_canvas(self, origin_id: str, train_number: int, dep_date: date | datetime | int | str) -> JSON:
        search = Utils.to_ms_date_timestamp(dep_date)

        url: str = f'{
            self.BASE_URI}/tratteCanvas/{origin_id}/{train_number}/{search}'
        r = requests.get(url)

        return r.json()

    def find_train_number_autocomplete(self, train_number: int) -> str:
        """Return a list of trains with the given number.
        A train number is not unique, so the list may contain more than
        one train. The format is 'train_number - departure_station|train_number-station_id-departure_date' whre departure_date is
        in ms since Epoch.
        """
        url: str = f'{
            self.BASE_URI}/cercaNumeroTrenoTrenoAutocomplete/{train_number}'
        r = requests.get(url)

        return r.text

    def autocomplete_station(self, text: str) -> str:
        """Return a list of stations starting with the given text.
        The format is 'station_name|station_id', where station_id is the
        one which starts with a letter and is followed by the actual
        station code padded with zeroes up to 5 digits).
        """

        url: str = f'{self.BASE_URI}/autocompletaStazione/{text}'
        r = requests.get(url)

        return r.text

    def language(self, idLingua) -> JSON:
        url: str = f'{self.BASE_URI}/language/{idLingua}'
        r = requests.get(url)

        return r.json()

    # TODO: add optional parameters date and time. They'll need to be
    # combined. If one of them is missing, it should default to the
    # current date/time. Make dt optional.
    def travel_solutions(self, origin_id: str, dest_id: str, dt: datetime) -> JSON:
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

        url: str = f'{
            self.BASE_URI}/soluzioniViaggioNew/{origin_id}/{dest_id}/{search_datetime}'
        r = requests.get(url)

        return r.json()

    def list_stations_city(self, stazione: str) -> JSON:
        url = f'{self.BASE_URI}/elencoStazioniCitta/{stazione}'
        r = requests.get(url)

        return r.json()

    def wheather(self, region_code: int) -> JSON:
        # I'm not sure about what the API returns when the region code is
        # 0, the codes are different than the ones found in the regions
        url: str = f'{self.BASE_URI}/datiMeteo/{region_code}'
        r = requests.get(url)

        return r.json()

    def station_detail(self, codiceStazione, codiceRegione: int) -> JSON:
        url: str = f'{
            self.BASE_URI}/dettaglioStazione/{codiceStazione}/{codiceRegione}'
        r = requests.get(url)

        return r.json()

    def stations_list(self, region_code: int) -> JSON:
        """Return the list of stations in the region with the given code."""
        url: str = f'{self.BASE_URI}/elencoStazioni/{region_code}'
        r = requests.get(url)

        return r.json()

    def autocomplete_station_set_trip(self, text: str) -> str:
        # It seems to return the same data as autocompleta_stazione
        url: str = f'{self.BASE_URI}/autocompletaStazioneImpostaViaggio/{text}'
        r = requests.get(url)

        return r.text

    def autocomplete_station_nts(self, text: str) -> str:
        """Return a list of stations starting with the given text.
        The format is 'station_name|station_id', but here station_id is
        formed by a code that identifies the manager of the station,
        followed by the actual station code padded with zeroes. Its length
        is always 9 digits (to be confirmed).
        """
        url: str = f'{self.BASE_URI}/autocompletaStazioneNTS/{text}'
        r = requests.get(url)

        return r.text

    def property(self, name) -> str:
        url: str = f'{self.BASE_URI}/property/{name}'
        r = requests.get(url)

        return r.json() if 'json' in r.headers['Content-Type'] else r.text

    def infomobilita_rss_box(self, isInfoLavori) -> HTML:
        url: str = f'{self.BASE_URI}/infomobilitaRSSBox/{isInfoLavori}'
        r = requests.get(url)

        return r.text

    def train_status(self, origin_id: str, train_number: int, dep_date: date | datetime | int | str) -> str:
        """Return the status of the given train at the given time.
        The origin id is the one returned by the API (which starts with
        a letter and is followed by the actual station code padded with
        zeroes up to 5 digits).
        """
        search = Utils.to_ms_date_timestamp(dep_date)

        url: str = f'{
            self.BASE_URI}/andamentoTreno/{origin_id}/{train_number}/{search}'
        r = requests.get(url)

        return r.json()

    def cerca_numero_treno(self, numeroTreno: int) -> JSON:
        url: str = f'{self.BASE_URI}/cercaNumeroTreno/{numeroTreno}'
        r = requests.get(url)

        return r.json()

    def infomobilita_ticker(self) -> HTML:
        url: str = f'{self.BASE_URI}/infomobilitaTicker'
        r = requests.get(url)

        return r.text

    def elenco_tratte(self, idRegione: int, zoomlevel, categoriaTreni, catAV, timestamp: int) -> JSON | str:
        url: str = f'{
            self.BASE_URI}/elencoTratte/{idRegione}/{zoomlevel}/{categoriaTreni}/{catAV}/{timestamp}'
        r = requests.get(url)

        return r.json() if 'json' in r.headers['Content-Type'] else r.text

    def cerca_programma_orario_destinazione_autocomplete(self, idStazionePartenza) -> JSON | str:
        url: str = f'{
            self.BASE_URI}/cercaProgrammaOrarioDestinazioneAutocomplete/{idStazionePartenza}'
        r = requests.get(url)

        return r.json() if 'json' in r.headers['Content-Type'] else r.text

    # TODO: controllare che non manchi un qualche parametro
    def dettaglio_viaggio(self, idStazioneDa, idStazioneA) -> JSON | str:
        url: str = f'{
            self.BASE_URI}/dettaglioViaggio/{idStazioneDa}/{idStazioneA}'
        r = requests.get(url)

        return r.json() if 'json' in r.headers['Content-Type'] else r.text

    def dettaglio_programma_orario(self, dataDa, dataA, idStazionePartenza, idStazioneArrivo) -> JSON | str:
        url: str = f'{self.BASE_URI}/dettaglioProgrammaOrario/{
            dataDa}/{dataA}/{idStazionePartenza}/{idStazioneArrivo}'
        r = requests.get(url)

        return r.json() if 'json' in r.headers['Content-Type'] else r.text

    def statistics(self) -> JSON:
        """Return statistics about trains.
        Even though the API requires a timestamp, it seems to ignore it and
        returns the same data regardless of the timestamp. Therefore, the
        timestamp is not required and defaults to the current time.
        """
        timestamp = int(datetime.now().timestamp() * 1000)

        url: str = f'{self.BASE_URI}/statistiche/{timestamp}'
        r = requests.get(url)

        return r.json()

    def find_station(self, text: str) -> JSON:
        """Return a list of stations starting with the given text."""
        url: str = f'{self.BASE_URI}/cercaStazione/{text}'
        r = requests.get(url)

        return r.json()

    def region(self, codiceStazione: str) -> int:
        # TODO: manipulate codiceStazione

        url: str = f'{self.BASE_URI}/regione/{codiceStazione}'
        r = requests.get(url)

        return int(r.text)

    def cerca_programma_orario_origine_autocomplete(self, arrival_station_id: str) -> JSON | str:
        url: str = f'{
            self.BASE_URI}/cercaProgrammaOrarioOrigineAutocomplete/{arrival_station_id}'
        r = requests.get(url)

        return r.json() if 'json' in r.headers['Content-Type'] else r.text

    def dettagli_tratta(self, idRegione, idTrattaAB, idTrattaBA, categoriaTreni, catAV) -> JSON | str:
        url: str = f'{self.BASE_URI}/dettagliTratta/{idRegione}/{
            idTrattaAB}/{idTrattaBA}/{categoriaTreni}/{catAV}'
        r = requests.get(url)

        return r.json() if 'json' in r.headers['Content-Type'] else r.text

    def infomobilita_rss(self, isInfoLavori) -> HTML:
        url: str = f'{self.BASE_URI}/infomobilitaRSS/{isInfoLavori}'
        r = requests.get(url)

        return r.text


class Utils:
    """A collection of utility functions."""
    vt = ViaggiaTreno()

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
