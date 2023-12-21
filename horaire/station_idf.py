from datetime import datetime

import requests

from database.database_idf import DatabaseIDF
from horaire.station import Station


def to_stif(string: str) -> str:
    if 'STIF' in string:
        return string
    if 'C' in string:
        return f"STIF:Line::{string[5:]}:"
    return f"STIF:StopPoint:Q:{string[5:]}:"


class StationIDF(Station):
    def __init__(self, id_station: str):
        database = DatabaseIDF()
        super().__init__(id_station, database)

        url = 'https://prim.iledefrance-mobilites.fr/marketplace/stop-monitoring'
        headers = {'Accept': 'application/json', 'apikey': '...'}
        params = {'MonitoringRef': to_stif(id_station)}
        try:
            requete = requests.get(url, headers=headers, params=params).json()
        except Exception as e:
            print(e)
            raise
        requete = requete['Siri']['ServiceDelivery']['StopMonitoringDelivery'][0]['MonitoredStopVisit']

        for entree in requete:
            id_arret = entree['MonitoringRef']['value']
            id_ligne = str(entree['MonitoredVehicleJourney']['LineRef']['value'])

            if id_ligne not in [o.id for o in self.lignes]:
                self.add_ligne(id_ligne)

            if id_arret not in [o.id for o in self.get_ligne(id_ligne).arrets]:
                self.get_ligne(id_ligne).add_arret(id_arret, database.get_nom_arret(id_arret))

            attente_depart = entree['MonitoredVehicleJourney']['MonitoredCall'].get(
                    'ExpectedDepartureTime', '2022-01-01T00:00:00.000Z')
            attente_arrivee = entree['MonitoredVehicleJourney']['MonitoredCall'].get(
                    'ExpectedArrivalTime', attente_depart)
            attente = datetime.strptime(attente_arrivee, '%Y-%m-%dT%H:%M:%S.%fZ')
            attente = round((attente - datetime.utcnow()).total_seconds() / 60.0)

            destination = entree['MonitoredVehicleJourney']['MonitoredCall'].get('DestinationDisplay')
            destination = entree['MonitoredVehicleJourney'].get('DestinationName', destination)
            destination = destination[0]['value']

            if entree['MonitoredVehicleJourney']["JourneyNote"] and entree['MonitoredVehicleJourney']['JourneyNote'][0]['value'] != "":
                destination = f"{entree['MonitoredVehicleJourney']['JourneyNote'][0]['value']} | {destination}"

            if attente >= 0:
                self.get_ligne(id_ligne).get_arret(id_arret).add_horaire(destination, attente)

    def rafraichir(self) -> None:
        self.__init__(self.id)

    def get_journey(self, id_arret: str, id_ligne: str) -> list[list]:
        return self._db.get_journey(id_arret, id_ligne)
