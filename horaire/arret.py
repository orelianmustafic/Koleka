class Arret:
    def __init__(self, id_arret: str, nom_arret: str):
        self.__id = id_arret
        self.__nom = nom_arret
        self.__horaires: dict[str, list[int]] = {}

    @property
    def id(self) -> str:
        return self.__id

    @property
    def nom(self) -> str:
        return self.__nom

    @property
    def horaires(self) -> dict[str, list[int]]:
        return self.__horaires

    def add_horaire(self, destination: str, attente: int):
        """Ajoute un horaire à la destination"""
        self.__horaires.setdefault(destination, []).append(attente)
