from sqlite3 import Connection

import requests
from rapidfuzz import fuzz
from unidecode import unidecode

from database.database import Database


def quick_difference(str1: str, str2: str) -> float:
    """Donne la similarité entre deux strings
    :param str1: La première chaîne de caractères
    :param str2: La deuxième chaîne de caractères
    :return: Chiffre entre 0 et 1 (1 étant le plus similaire)
    """
    return fuzz.ratio(unidecode(str1.casefold()), unidecode(str2.casefold()))


class DatabaseTBM(Database):
    def __init__(self):
        super().__init__(r"./database/bases/database_tbm.sqlite")

    def update(self) -> None:
        self.clear_tables()

        cle = '...'
        url = 'https://data.bordeaux-metropole.fr/geojson'
        donnees = {
            'sv_ligne_a': """INSERT OR REPLACE INTO ligne(GID, libelle, identifiant, vehicule, active, SAE, QUALITE_PLUS, CDATE, MDATE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            'sv_arret_p': """INSERT OR REPLACE INTO arret(GID, geom_o, geom_err, identifiant, numero, groupe, num_ordre, libelle, vehicule, type, actif, voirie, INSEE, source, CDATE, MDATE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            'sv_chem_l': """INSERT OR REPLACE INTO chemin(GID, geom_err, libelle, via, sens, vehicule, principal, groupe, rs_sv_ligne_a, rg_sv_arret_p_nd, rg_sv_arret_p_na, CDATE, MDATE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            'sv_cours_a': """INSERT OR REPLACE INTO course(GID, etat, partielle, rs_sv_ligne_a, rs_sv_chem_l, rg_sv_arret_p_nd, rg_sv_arret_p_na, CDATE, MDATE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            'sv_horai_a': """INSERT OR REPLACE INTO temps(GID, hor_theo, hor_app, hor_estime, hor_real, tempsarret, etat, type, source, rs_sv_arret_p, rs_sv_cours_a, CDATE, MDATE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        }

        for i, e in donnees.items():
            params = {'key': cle, 'typename': i}
            requete = requests.get(url, params=params).json()
            cur = self.conn.cursor()
            for f in requete['features']:
                cur.execute(e, list(f['properties'].values()))
            cur.connection.commit()

    def get_horaires(self, arrets: list[str]) -> list:
        cur = self.conn.cursor()

        cur.execute(f''' SELECT *
                        FROM Temps
                        WHERE rs_sv_arret_p IN {tuple(arrets)} AND etat = 'NON_REALISE'
                        ORDER BY hor_estime;
                                ''')

        rows = cur.fetchall()
        cur.close()
        return rows

    def get_destination(self, course: str) -> str:
        cur = self.conn.cursor()

        cur.execute(''' SELECT Libelle
                        FROM Arret
                        WHERE GID IN (
                            SELECT rg_sv_arret_p_na
                            FROM Course
                            WHERE GID = ?
                            );
                    ''', (course,))

        rows = cur.fetchall()
        cur.close()

        return rows[0][0] if rows else ""

    def get_arrets(self, nom_arret: str) -> list:
        cur = self.conn.cursor()
        self.conn.create_function("sql_getDifference", 2, quick_difference)

        cur.execute(''' SELECT DISTINCT Arret.*, sql_getDifference(Arret.libelle, ?) AS Diff
                        FROM Arret
                        ORDER BY Diff DESC
                        LIMIT 25;
                        ''', (nom_arret,))

        rows = cur.fetchall()
        cur.close()
        return rows

    def get_nearest_city(self, longitude: float, latitude: float) -> str:
        pass

    def get_color(self, id_ligne: str) -> hex:
        return None

    def get_nom_arret(self, id_arret: str) -> str:
        cur = self.conn.cursor()

        cur.execute(''' SELECT Arret.libelle
                        FROM Arret
                        WHERE Arret.GID = ?;
                    ''', (id_arret,))

        rows = cur.fetchall()
        cur.close()
        return " " if not rows else rows[0][0]

    def get_journey(self, id_arret: str, id_ligne: str) -> list[str]:
        pass

    def add_emoji(self, ligne: str, emoji: str) -> None:
        pass

    def get_emoji(self, ligne: str) -> str:
        cur = self.conn.cursor()

        cur.execute(''' SELECT Ligne.libelle
                        FROM Ligne
                        WHERE Ligne.GID = ?
                        ''', (ligne,))

        rows = cur.fetchall()
        cur.close()
        return "" if not rows else rows[0][0]

    def get_ligne(self, ligne: str) -> list[str]:
        cur = self.conn.cursor()

        cur.execute(''' SELECT Ligne.GID
                        FROM Ligne
                        WHERE Ligne.libelle = ? OR Ligne.Identifiant = ?;
                        ''', (ligne, ligne,)
                    )

        rows = cur.fetchall()
        cur.close()
        return [] if not rows else [i[0] for i in rows]

    def get_ligne_course(self, course: str) -> str:
        cur = self.conn.cursor()

        cur.execute('''SELECT Course.rs_sv_ligne_a
                                FROM Course
                                WHERE Course.GID = ?
                                ''', (course,))

        rows = cur.fetchall()
        return rows[0][0] if rows else []

    def get_nom_ligne(self, ligne: str) -> str:
        """Fournit la société en charge de la ligne
            :param ligne:  L'identifiant de la ligne (Type STIF:Line::XXXXXX:)
            :return: Si on n'a pas trouvé d'occurrences = None, sinon le nom de la ligne
            """
        cur = self.conn.cursor()

        cur.execute(''' SELECT Ligne.libelle
                        FROM Ligne
                        WHERE Ligne.GID = ?
                        ''', (ligne,))

        rows = cur.fetchall()
        cur.close()
        return None if not rows else rows[0][0]

    def clear_tables(self) -> None:
        cur = self.conn.cursor()

        for i in ['arret', 'chemin', 'course', 'ligne', 'temps']:
            cur.execute(f'''DELETE FROM {i}''')

        cur.connection.commit()
        cur.close()
