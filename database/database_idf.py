from sqlite3 import Cursor
from typing import Any

from database.database_gtfs import DatabaseGTFS
from database.shapegeocode import geocoder


def to_stif(string: str) -> str:
    """Convertit au format STIF toute chaîne de caractères"""
    if 'STIF' in string:
        return string
    if 'C' in string:
        return f"STIF:Line::{string[5:]}:"
    return f"STIF:StopPoint:Q:{string[5:]}:"


def to_idfm(string: str) -> str:
    """Convertit au format IDFM toute chaîne de caractères"""
    if 'IDFM' in string:
        return string
    if 'Line' in string:
        return f"IDFM:{string[11:-1]}"
    return f"IDFM:{string[17:-1]}"


class DatabaseIDF(DatabaseGTFS):
    def __init__(self):
        super().__init__(r"./database/bases/idfm.sqlite")

    def get_color(self, id_ligne: str) -> hex:
        return super().get_color(to_idfm(id_ligne))

    def get_nom_arret(self, id_arret: str) -> str:
        return super().get_nom_arret(to_idfm(id_arret))

    def get_journey(self, id_arret: str, id_ligne: str) -> list[list[Any]]:
        return super().get_journey(to_idfm(id_arret), to_idfm(id_ligne))

    def get_emoji(self, ligne: str) -> str:
        return super().get_emoji(to_idfm(ligne))

    def get_ligne(self, ligne: str) -> list[str]:
        return [to_stif(i) for i in super().get_ligne(ligne)]

    def get_nom_ligne(self, ligne: str) -> str:
        return super().get_nom_ligne(to_idfm(ligne))

    def get_agency(self, ligne: str) -> str:
        return super().get_agency(to_idfm(ligne))

    def get_horaires(self, arret: str) -> list[list]:
        return super().get_horaires(to_idfm(arret))

    def update_cities(self) -> None:
        gc = geocoder('./communes/communes-dile-de-france-au-01-janvier.shp')

        def get_city(lat, lon) -> str:
            ville = gc.geocode(float(lat), float(lon), max_dist=20)
            return ville['nomcom'] if ville else ""

        cur = self.conn.cursor()
        self.conn.create_function("sql_getCity", 2, get_city)

        cur.execute("""UPDATE Stops SET ville = sql_getCity(lat, lon)""")

        cur.connection.commit()
        cur.close()


if __name__ == '__main__':
    db = DatabaseIDF()

    sql_create_agency_table = """ CREATE TABLE IF NOT EXISTS agency (
                                            id text PRIMARY KEY,
                                            name text NOT NULL,
                                            url text,
                                            timezone text,
                                            lang text,
                                            phone text,
                                            email text
                                        ); """

    sql_create_routes_table = """CREATE TABLE IF NOT EXISTS routes (
                                        id text PRIMARY KEY,
                                        agency_id text REFERENCES agency (id),
                                        short_name text,
                                        long_name text,
                                        desc text,
                                        type integer,
                                        url text,
                                        color text,
                                        text_color text,
                                        sort_order text,
                                        emoji text
                                    );"""

    sql_create_trips_table = """CREATE TABLE IF NOT EXISTS trips (
                                route_id text REFERENCES routes (id),
                                service_id text,
                                id text,
                                headsign text,
                                short_name text,
                                direction_id integer,
                                block_id text,
                                shape_id text,
                                wheelchair_accessible integer,
                                bikes_allowed integer,
                                PRIMARY KEY (route_id, service_id, id)
                                )"""

    sql_create_stops_table = """CREATE TABLE IF NOT EXISTS stops (
                                    id text PRIMARY KEY,
                                    code text,
                                    name text,
                                    desc text,
                                    lon text,
                                    lat text,
                                    zone_id integer,
                                    url text,
                                    location_type integer,
                                    parent_station text REFERENCES stops (id),
                                    timezone text,
                                    level_id text,
                                    wheelchair_boarding integer,
                                    platform_code text,
                                    ville text
                                    )"""

    sql_create_stop_times_table = """CREATE TABLE IF NOT EXISTS stop_times (
                                trip_id text REFERENCES trips (id),
                                arrival_time text,
                                departure_time text,
                                stop_id text REFERENCES stops (id),
                                stop_sequence integer,
                                pickup_type integer,
                                drop_off_type integer,
                                local_zone_id text,
                                stop_headsign text,
                                timepoint integer,
                                PRIMARY KEY (trip_id, stop_sequence)
                                )"""

    sql_create_cities_table = """CREATE TABLE IF NOT EXISTS cities (
                                   id text PRIMARY KEY,
                                   name text,
                                   latitude text,
                                   longitude text
                                   )"""

    # Création des tables
    if db.conn is not None:
        cur_create: Cursor = db.conn.cursor()

        cur_create.execute(sql_create_agency_table)
        cur_create.execute(sql_create_routes_table)
        cur_create.execute(sql_create_trips_table)
        cur_create.execute(sql_create_stops_table)
        cur_create.execute(sql_create_stop_times_table)
        cur_create.execute(sql_create_cities_table)

        cur_create.close()
    else:
        print("Error! cannot create the database connection.")
