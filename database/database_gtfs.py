import itertools
from abc import ABC
from datetime import datetime
from typing import Any

from fuzzywuzzy import fuzz
from unidecode import unidecode

from database.database import Database


def quick_difference(str1: str, str2: str) -> float:
    """Donne la similarité entre deux strings
    :param str1: La première chaîne de caractères
    :param str2: La deuxième chaîne de caractères
    :return: Chiffre entre 0 et 1 (1 étant le plus similaire)
    """
    return fuzz.ratio(unidecode(str1.casefold()), unidecode(str2.casefold()))


class DatabaseGTFS(Database, ABC):
    def get_arrets(self, nom_arret: str) -> list:
        cur = self.conn.cursor()
        self.conn.create_function("sql_getDifference", 2, quick_difference)

        cur.execute(''' SELECT DISTINCT S2.*, sql_getDifference(S2.name, ?) AS Diff
                        FROM Stops AS S1 INNER JOIN Stops AS S2 ON S1.parent_station = S2.id
                        ORDER BY Diff DESC
                        LIMIT 25
                    ''', (nom_arret,))

        rows = cur.fetchall()
        cur.close()
        return rows

    def get_color(self, id_ligne: str) -> hex:
        cur = self.conn.cursor()

        cur.execute(''' SELECT R.color
                        FROM Routes as R
                        WHERE R.id = ? or R.short_name = ?;
                    ''', (id_ligne, id_ligne))

        row = cur.fetchall()
        cur.close()
        return 0x2F3136 if not row else int(row[0][0], 16)

    def get_nom_arret(self, id_arret: str) -> str:
        cur = self.conn.cursor()

        cur.execute(''' SELECT S.name
                        FROM Stops AS S
                        WHERE S.id = ?;
                    ''', (id_arret,))

        rows = cur.fetchall()
        cur.close()
        return " " if not rows else unidecode(rows[0][0])

    def get_journey(self, id_arret: str, id_ligne: str) -> list[list[Any]]:
        cur = self.conn.cursor()

        arrets = tuple(i[0] for i in cur.execute(
                f"""SELECT DISTINCT S.id FROM STOPS S WHERE S.id = '{id_arret}' OR S.parent_station = '{id_arret}'""").fetchall())
        arrets_sql = ",".join(["?"] * len(arrets))

        cur.execute(f'''SELECT st.stop_id, st.stop_sequence, st.arrival_time, st.departure_time
                        FROM stop_times AS st
                        WHERE st.trip_id IN (
                            SELECT trip_id
                            FROM (stop_times st INNER JOIN stops s on s.id = st.stop_id) INNER JOIN trips t on t.id = st.trip_id
                            WHERE st.stop_id IN ({arrets_sql}) AND t.route_id = '{id_ligne}'
                            GROUP BY stop_sequence, stop_id)
                    ''', arrets)
        rows = cur.fetchall()

        journey = []
        tmp_trip = []
        trouver_nouveau_trajet = False

        for i, arret in enumerate(rows):
            # Si jamais on a trouvé notre arrêt, on navigue jusqu'au prochain trajet (stop_sequence à 0)
            if arret[1] != 0 and trouver_nouveau_trajet:
                continue

            trouver_nouveau_trajet = False
            temps = 0

            if arret[1] != 0:
                t1 = datetime.strptime(f"{int(arret[2][:2]) % 24:02}{arret[2][2:]}", '%H:%M:%S')
                t2 = datetime.strptime(f"{int(rows[i - 1][3][:2]) % 24:02}{rows[i - 1][3][2:]}", '%H:%M:%S')

                temps = (t1 - t2).total_seconds() / 60 - 0.5
                temps = 0.5 if (temps < 0) and i else temps

            tmp_trip.append((arret[0], arret[1], temps))

            # On s'arrête dès lors qu'on a trouvé notre arrêt
            if arret[0] in arrets:
                journey.append(tmp_trip)
                tmp_trip = []
                trouver_nouveau_trajet = True

        iterable = sorted(journey, key=lambda x: x[0] and len(x))
        groups = [list(x[1]) for x in itertools.groupby(iterable, lambda x: x[0])]
        journey = [items[0] for items in groups]
        journey.reverse()

        '''journey_id = [[arret[0] for arret in trajet] for trajet in journey]

        for i, trajet in enumerate(journey):
            for e, trajet2 in enumerate(journey[i + 1:]):
                if all(item in journey_id[i] for item in journey_id[e]):
                    journey.remove(trajet2)'''

        return journey

    def add_emoji(self, ligne: str, emoji: str) -> None:
        cur = self.conn.cursor()

        cur.execute(''' UPDATE Routes
                        SET emoji = ?
                        WHERE Routes.short_name = ? OR routes.long_name = ?
                        AND Routes.agency_id IN ('IDFM:71', 'IDFM:55', 'IDFM:Operator_100', 'IDFM:1046')
                    ''', (emoji, ligne, ligne,))

        cur.connection.commit()
        cur.close()

    def get_emoji(self, ligne: str) -> str:
        cur = self.conn.cursor()

        cur.execute(''' SELECT Routes.short_name, Routes.emoji
                        FROM Routes
                        WHERE Routes.id = ? or Routes.short_name = ?
                    ''', (ligne, ligne))

        rows = cur.fetchall()
        cur.close()

        if not rows:
            return ligne
        if not rows[0][1]:
            return rows[0][0]

        return rows[0][1]

    def get_ligne(self, ligne: str) -> list[str]:
        cur = self.conn.cursor()

        cur.execute(''' SELECT Routes.id
                        FROM Routes
                        WHERE Routes.short_name = ? OR routes.long_name = ?
                    ''', (ligne, ligne))

        rows = cur.fetchall()
        cur.close()
        return [] if not rows else [i[0] for i in rows]

    def get_nom_ligne(self, ligne: str) -> str:
        cur = self.conn.cursor()

        cur.execute(''' SELECT Routes.short_name
                        FROM Routes
                        WHERE Routes.id = ?
                    ''', (ligne,))

        rows = cur.fetchall()
        cur.close()
        return None if not rows else rows[0][0]

    def get_agency(self, ligne: str) -> str:
        cur = self.conn.cursor()

        cur.execute(''' SELECT Routes.agency_id
                        FROM Routes
                        WHERE Routes.id = ?
                    ''', (ligne,))

        rows = cur.fetchall()
        cur.close()
        return None if not rows else rows[0][0]

    def get_horaires(self, arret: str) -> list[list]:
        cur = self.conn.cursor()

        cur.execute(''' SELECT *
                        FROM stop_times
                        WHERE stop_id IN (SELECT id FROM stops WHERE parent_station = ? or id = ?)
                        ORDER BY arrival_time
                            ''', (arret, arret,))

        rows = cur.fetchall()
        cur.close()
        return [] if not rows else rows

    def clear_tables(self) -> None:
        cur = self.conn.cursor()

        for i in ['agency', 'routes', 'trips', 'stop_times', 'stops']:
            cur.execute(f'''DELETE FROM {i}''')

        cur.connection.commit()
        cur.close()
