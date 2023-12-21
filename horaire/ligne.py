from typing import overload

from sortedcontainers import SortedSet

from horaire.arret import Arret


class Ligne:
    def __init__(self, id_ligne: str, emoji: str, couleur: str):
        self.__id = id_ligne
        self.__emoji = emoji
        self.__couleur = couleur
        self.__arrets: SortedSet[Arret] = SortedSet(key=lambda arret: arret.id)

    @property
    def id(self) -> str:
        return self.__id

    @property
    def emoji(self) -> str:
        return self.__emoji

    @property
    def couleur(self) -> hex:
        return self.__couleur

    @property
    def arrets(self) -> list[Arret]:
        return list(self.__arrets)

    @overload
    def get_arret(self, param: int = 0) -> Arret:
        ...

    @overload
    def get_arret(self, param: str) -> Arret:
        ...

    def get_arret(self, param=0) -> Arret:
        """Donne un arrêt à l'indice donné ou à la correspondance de son nom"""
        if isinstance(param, int):
            return self.arrets[param]
        if isinstance(param, str):
            return next((x for x in self.arrets if x.id == param), None)

    def add_arret(self, id_arret: str, nom_arret: str) -> None:
        """Ajoute un arrêt"""
        arret = Arret(id_arret, nom_arret)
        self.__arrets.add(arret)
