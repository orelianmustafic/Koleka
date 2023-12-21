from datetime import datetime

import pytz

from database.database_tbm import DatabaseTBM
from horaire.station import Station


class StationTBM(Station):
    def __init__(self, id_station: list[str]):
        database = DatabaseTBM()
        super().__init__(id_station[0], database)

        horaires = database.get_horaires(id_station)

        for entree in horaires:
            id_arret = entree[-1]
            id_ligne = database.get_ligne_course(entree[-2])

            if id_ligne not in [o.id for o in self.lignes]:
                self.add_ligne(id_ligne)

            if id_arret not in [o.id for o in self.get_ligne(id_ligne).arrets]:
                self.get_ligne(id_ligne).add_arret(id_arret, database.get_nom_arret(id_arret))

            attente = datetime.strptime(entree[8], '%Y-%m-%dT%H:%M:%S%z')
            attente = round((attente - datetime.now(pytz.utc)).total_seconds() / 60.0)

            destination = database.get_destination(entree[-2])

            if attente >= 0:
                self.get_ligne(id_ligne).get_arret(id_arret).add_horaire(destination, attente)

    def get_journey(self, num_page: int, num_direction: int) -> list[str]:
        # TODO document why this method is empty
        pass

    def rafraichir(self) -> None:
        self.__init__([self.id])
