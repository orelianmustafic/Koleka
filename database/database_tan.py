from database.database_gtfs import DatabaseGTFS


class DatabaseTAN(DatabaseGTFS):
    def __init__(self):
        super().__init__(r"./database/bases/database_tan.sqlite")
