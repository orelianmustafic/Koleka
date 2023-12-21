from abc import ABC, abstractmethod
from typing import Any, overload

from sortedcontainers import SortedSet

from database.database import Database
from horaire.ligne import Ligne


class Station(ABC):
    def __init__(self, id_station: str, database: Database):
        self._db: Database = database
        self.__id: str = id_station
        self.__nom: str = self._db.get_nom_arret(id_station)
        self.__lignes: SortedSet[Ligne] = SortedSet(key=lambda ligne: ligne.id)

    @property
    def id(self) -> str:
        return self.__id

    @property
    def nom(self) -> str:
        return self.__nom

    @property
    def lignes(self) -> list[Ligne]:
        return list(self.__lignes)

    @overload
    def get_ligne(self, param: int = 0) -> Ligne | None:
        ...

    @overload
    def get_ligne(self, param: str) -> Ligne | None:
        ...

    def get_ligne(self, param=0) -> Ligne | None:
        """Donne une ligne à l'indice donné ou à la correspondance de son nom"""
        if not self.lignes:
            return None
        if isinstance(param, int):
            param %= len(self.lignes)
            return self.lignes[param % len(self.lignes)]
        if isinstance(param, str):
            return next((x for x in self.lignes if x.id == param), None)

    def add_ligne(self, id_ligne: str) -> None:
        """Ajoute une ligne"""
        ligne = Ligne(id_ligne, self._db.get_emoji(id_ligne), self._db.get_color(id_ligne))
        self.__lignes.add(ligne)

    def get_index_ligne(self, nom_ligne: str):
        """Donne l'indice dans la liste en correspondance avec son nom"""
        try:
            id_lignes_utilisateur = self._db.get_ligne(nom_ligne.upper())
            id_lignes_arret = [x.id for x in self.lignes]
            return [id_lignes_arret.index(x) for x in id_lignes_utilisateur if x in id_lignes_arret][0]
        except (ValueError, IndexError, AttributeError):
            return 0

    @abstractmethod
    def rafraichir(self) -> None:
        """Rafraîchit les horaires de la station"""
        pass

    @abstractmethod
    def get_journey(self, id_arret: str, id_ligne: str) -> list[list[Any]]:
        """Obtient tous les itinéraires d'une ligne donnée passant par l'arrêt donné"""
        pass
