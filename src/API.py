import json
import logging
import pathlib

import requests

base_url = "http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"
logging.basicConfig(level=logging.WARNING)

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


def get(method, *params):
    """call the ViaggiaTreno API with the given method and parameters."""
    url = f'{base_url}/{method}/{"/".join(str(p) for p in params)}'

    r = requests.get(url)

    if r.status_code != 200:
        logging.error(f'Error {r.status_code} while calling {url}: {r.text}')
        return None

    filename = f'{method} ({", ".join(str(p) for p in params)}) [{r.headers["Date"]}]'
    if (logging.getLogger().getEffectiveLevel() == logging.DEBUG):
        pathlib.Path('responses').mkdir(parents=True, exist_ok=True)
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
