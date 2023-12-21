import sqlite3
from sqlite3 import Connection, Error
import discord


class DatabaseUsers:
    conn: Connection

    def __init__(self):
        self.conn = sqlite3.connect(r"./database/bases/database_users.sqlite")

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

    def add_favori(self, user: discord.User, id_station: str) -> None:
        cur = self.conn.cursor()
        cur.execute('''INSERT INTO favori(user_id, station) VALUES (?, ?)''', (user.id, id_station))
        """index = cur.execute('''SELECT MAX(favori._id) FROM favori''').fetchall()[0][0]
        for i in lignes:
            cur.execute('''INSERT INTO favori_lignes(station, ligne) VALUES (?, ?)''', (index, i))"""

        cur.connection.commit()
        cur.close()

    def remove_favori(self, user: discord.User, id_station: str) -> None:
        cur = self.conn.cursor()
        cur.execute('''DELETE FROM favori_lignes WHERE station = (SELECT _id FROM favori WHERE user_id = ? AND station = ?)''', (user.id, id_station,))
        cur.execute('''DELETE FROM favori WHERE user_id = ? AND station = ?''', (user.id, id_station,))
        cur.connection.commit()
        cur.close()

    def get_favoris(self, user: discord.User) -> list[str]:
        cur = self.conn.cursor()
        cur.execute('''SELECT favori.station from favori where user_id = ?''', (str(user.id),))

        rows = cur.fetchall()
        cur.close()
        return None if not rows else [i[0] for i in rows]

    def get_lignes_favoris(self, user: discord.User, station: str) -> list[str]:
        cur = self.conn.cursor()
        cur.execute('''SELECT favori_lignes.ligne from favori inner join favori_lignes on favori._id = favori_lignes.station where user_id = ? and favori.station = ?''', (str(user.id), station,))

        rows = cur.fetchall()
        cur.close()
        return None if not rows else [i[0] for i in rows]


if __name__ == '__main__':
    db = DatabaseUsers()

    sql_create_favoris_table = """ CREATE TABLE favori (
                                    _id INTEGER PRIMARY KEY AUTOINCREMENT ,
                                    user_id text NOT NULL,
                                    station text NOT NULL,
                                    UNIQUE (user_id, station)
                                ); """

    sql_create_favoris_lignes_table = """ CREATE TABLE favori_lignes (
                                            _id INTEGER PRIMARY KEY AUTOINCREMENT ,
                                            station text NOT NULL REFERENCES favori(_id),
                                            ligne text NOT NULL,
                                            UNIQUE (station, ligne)
                                        ); """

    # Création des tables
    if db.conn is not None:
        db.create_table(sql_create_favoris_table)
        db.create_table(sql_create_favoris_lignes_table)
    else:
        print("Error! cannot create the database connection.")
