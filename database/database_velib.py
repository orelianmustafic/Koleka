import json
import sqlite3
from sqlite3 import Connection, Error

import requests
from rapidfuzz import fuzz
from unidecode import unidecode


def quick_difference(str1: str, str2: str) -> float:
    """Donne la similarité entre deux strings
    :param str1: La première chaîne de caractères
    :param str2: La deuxième chaîne de caractères
    :return: Chiffre entre 0 et 1 (1 étant le plus similaire)
    """
    return fuzz.ratio(unidecode(str1.casefold()), unidecode(str2.casefold()))


class DatabaseVelib:
    conn: Connection

    def __init__(self):
        self.conn = sqlite3.connect(r"./database/bases/database_velib.sqlite")

    def create_table(self, create_table_sql) -> None:
        """ create a table from the create_table_sql statement
        :param create_table_sql: a CREATE TABLE statement
        """
        try:
            cur = self.conn.cursor()
            cur.execute(create_table_sql)
            cur.close()
        except Error as e:
            print(e)

    def refresh_info(self):
        cur = self.conn.cursor()
        url = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_information.json"

        open('./station_information.json', 'wb').write(requests.get(url).content)
        with open('./station_information.json', encoding='utf-8') as f:
            dico = json.load(f)['data']['stations']

            for _, value in enumerate(dico):
                cur.execute(
                        '''INSERT OR REPLACE INTO informations(station_id, name, lat, lon, capacity, stationCode) VALUES (?, ?, ?, ?, ?, ?)''',
                        (value['station_id'], value['name'], value['lat'], value['lon'], value['capacity'],
                         value['stationCode']))

            cur.connection.commit()

    def refresh_status(self):
        cur = self.conn.cursor()
        url = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json"

        open('./station_status.json', 'wb').write(requests.get(url).content)
        with open('./station_status.json', encoding='utf-8') as f:
            dico = json.load(f)['data']['stations']

            for _, value in enumerate(dico):
                cur.execute(
                        '''INSERT OR REPLACE INTO status(stationCode, station_id, numBikesAvailable, numBikesElec, numBikesMeca, numDocksAvailable, isInstalled, isReturning, isRenting, lastReported) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (value['stationCode'], value['station_id'], value['numBikesAvailable'],
                         value['num_bikes_available_types'][0]['mechanical'],
                         value['num_bikes_available_types'][1]['ebike'], value['numDocksAvailable'],
                         value['is_installed'], value['is_returning'], value['is_renting'], value['last_reported']))

            cur.connection.commit()

    def get_stations(self, nom_station: str) -> list:
        cur = self.conn.cursor()
        self.conn.create_function("sql_getDifference", 2, quick_difference)

        cur.execute(''' SELECT DISTINCT i.*, sql_getDifference(i.name, ?) AS Diff
                        FROM informations i
                        ORDER BY Diff DESC
                        LIMIT 25
                        ''', (nom_station,))

        rows = cur.fetchall()
        cur.close()

        return rows

    def get_status(self, id_station: str):
        cur = self.conn.cursor()
        self.conn.create_function("sql_getDifference", 2, quick_difference)

        cur.execute(''' SELECT DISTINCT s.*
                        FROM status s
                        WHERE s.station_id = ?
                        LIMIT 25
                        ''', (id_station,))

        rows = cur.fetchall()
        cur.close()

        return rows


if __name__ == '__main__':
    db = DatabaseVelib()

    sql_create_informations_table = """CREATE TABLE informations (
                                            station_id INTEGER PRIMARY KEY,
                                            name TEXT,
                                            lat TEXT,
                                            lon TEXT,
                                            capacity INTEGER,
                                            stationCode TEXT
                                        ); """

    sql_create_status_table = """CREATE TABLE status (
                                    stationCode TEXT REFERENCES informations(stationCode),
                                    station_id INTEGER REFERENCES informations(station_id),
                                    numBikesAvailable INTEGER,
                                    numBikesElec INTEGER,
                                    numBikesMeca INTEGER,
                                    numDocksAvailable INTEGER,
                                    isInstalled BOOLEAN,
                                    isReturning BOOLEAN,
                                    isRenting BOOLEAN,
                                    lastReported INTEGER,
                                    PRIMARY KEY(stationCode, station_id)
                                ); """

    # Création des tables
    if db.conn is not None:
        db.create_table(sql_create_informations_table)
        db.create_table(sql_create_status_table)
    else:
        print("Error! cannot create the database connection.")

    db.refresh_info()
    db.refresh_status()
