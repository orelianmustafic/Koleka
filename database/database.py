from abc import ABC, abstractmethod

import sqlite3
from sqlite3 import Connection
from typing import Any
import pandas as pd


class Database(ABC):
    conn: Connection
    path: str

    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(path)

    def insert_data(self, file: str, table: str, columns: dict) -> None:
        """Insert des données depuis un fichier CSV
        :param file: Chemin du fichier
        :param table: Table où insérer les données
        :param columns: Colonnes correspondantes au fichier
        """
        f = pd.read_csv(file, low_memory=False)

        rename = {f.columns[i]: columns[i] for i in range(len(f.columns))}
        f.rename(columns=rename, inplace=True)

        f.to_sql(table, self.conn, if_exists='append', index=False)

    @abstractmethod
    def get_arrets(self, nom_arret: str) -> list:
        """Fournit tous les arrêts depuis la base de données

        :param nom_arret: Le nom de l'arrêt en toutes lettres
        :return: une liste correspondant au resultat de la recherche
        """
        pass

    @abstractmethod
    def get_color(self, id_ligne: str) -> hex:
        """Fournit depuis la base de données la couleur d'une ligne

        :param id_ligne: L'identifiant de la ligne
        :return: Code hexadécimal
        """
        pass

    @abstractmethod
    def get_nom_arret(self, id_arret: str) -> str:
        """Fournit depuis la base de données le nom d'un arrêt

        :param id_arret: L'identifiant de l'arrêt
        :return: Le nom de l'arrêt
        """
        pass

    @abstractmethod
    def get_journey(self, id_arret: str, id_ligne: str) -> list[list[Any]]:
        """Recherche dans la base de donnée un trajet entier

        :param id_arret: L'identifiant de l'arrêt
        :param id_ligne: L'identifiant de la ligne
        :return: Liste de tous les arrêts précédant notre arrêt
        """
        pass

    @abstractmethod
    def add_emoji(self, ligne: str, emoji: str) -> None:
        """Ajoute un emoji à la base de données"""
        pass

    @abstractmethod
    def get_emoji(self, ligne: str) -> str:
        """Fournit un emoji depuis la base de données

        :param ligne: L'identifiant de la ligne
        :return: Si l'émoji n'est pas trouvé, le nom de la ligne, sinon l'émoji en question
        """
        pass

    @abstractmethod
    def get_ligne(self, ligne: str) -> list[str]:
        """Fournit un emoji depuis la base de données

        :param ligne: Le nom commun de la ligne (ex : 42, PC, A)
        :return: Si on n'a pas trouvé d'occurrences = None, sinon une liste d'identifiants
        """
        pass

    @abstractmethod
    def get_nom_ligne(self, ligne: str) -> str:
        """Fournit la société en charge de la ligne

        :param ligne:  L'identifiant de la ligne
        :return: Si on n'a pas trouvé d'occurrences = None, sinon le nom de la ligne
        """
        pass

    @abstractmethod
    def clear_tables(self) -> None:
        """Supprime toutes les tables de la base de données"""
        pass
