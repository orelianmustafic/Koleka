import requests

from database.database_tan import DatabaseTAN
from horaire.station import Station


class StationTAN(Station):
    def __init__(self, id_station: str):
        database = DatabaseTAN()
        super().__init__(id_station, database)

        url = f'https://open.tan.fr/ewp/tempsattente.json/{id_station}'
        try:
            requete = requests.get(url).json()
        except Exception as e:
            print(e)
            raise

        for entree in requete:
            if entree['tempsReel'] == "false":
                continue

            id_arret = entree['arret']['codeArret']
            id_ligne = entree['ligne']['numLigne']

            if id_ligne not in [o.id for o in self.lignes]:
                self.add_ligne(id_ligne)

            if id_arret not in [o.id for o in self.get_ligne(id_ligne).arrets]:
                self.get_ligne(id_ligne).add_arret(id_arret, database.get_nom_arret(id_arret))

            if entree['temps'] == 'proche':
                attente = 0
            else:
                attente = int(''.join(filter(str.isdigit, entree['temps'])))

            destination = entree['terminus']

            if attente >= 0:
                self.get_ligne(id_ligne).get_arret(id_arret).add_horaire(destination, attente)

    def get_journey(self, id_arret: str, id_ligne: str) -> list[list]:
        return self._db.get_journey(id_arret, id_ligne)

    def rafraichir(self) -> None:
        self.__init__(self.id)
