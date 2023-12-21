import datetime
import os
import threading
import zipfile
from enum import Enum

import requests
from discord.ext import commands, tasks

from database.database_idf import DatabaseIDF
from database.database_tan import DatabaseTAN
from database.database_tbm import DatabaseTBM


class Bases(Enum):
    IDFM = {'database': DatabaseIDF(),
            'path': './IDFM-gtfs.zip',
            'folder': 'idfm',
            'url': 'https://data.iledefrance-mobilites.fr/api/datasets/1.0/offre-horaires-tc-gtfs-idfm/images/a925e164271e4bca93433756d6a340d1',
            'columns': {
                "agency": ['id', 'name', 'url', 'timezone', 'lang', 'phone', 'email'],
                "routes": ['id', 'agency_id', 'short_name', 'long_name', 'desc', 'type', 'url', 'color', 'text_color', 'sort_order'],
                "trips": ['route_id', 'service_id', 'id', 'headsign', 'short_name', 'direction_id', 'block_id', 'shape_id', 'wheelchair_accessible', 'bikes_allowed'],
                "stop_times": ['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence', 'pickup_type', 'drop_off_type', 'local_zone_id', 'stop_headsign', 'timepoint'],
                "stops": ['id', 'code', 'name', 'desc', 'lon', 'lat', 'zone_id', 'url', 'location_type', 'parent_station', 'timezone', 'level_id', 'wheelchair_boarding', 'platform_code'],
                "cities": ['id', 'name', 'latitude', 'longitude'],
                "stops_routes": ['route_id', 'route_long_name', 'plans', 'schedules', 'stop_id', 'stop_name', 'lon', 'lat', 'operatorName', 'pointGeo', 'nomCommune', 'codeInsee']}
            }

    TAN = {'database': DatabaseTAN(),
           'path': './gtfs-tan.zip',
           'folder': 'tan',
           'url': 'https://data.nantesmetropole.fr/api/explore/v2.1/catalog/datasets/244400404_tan-arrets-horaires-circuits/files/16a1a0af5946619af621baa4ad9ee662',
           'columns': {
               "agency": ['id', 'name', 'url', 'timezone', 'lang', 'phone'],
               "routes": ['id', 'short_name', 'long_name', 'desc', 'type', 'color', 'text_color', 'sort_order'],
               "trips": ['route_id', 'service_id', 'id', 'headsign', 'direction_id', 'block_id', 'shape_id', 'wheelchair_accessible'],
               "stop_times": ['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence', 'pickup_type', 'drop_off_type', 'timepoint', 'stop_headsign'],
               "stops": ['id', 'name', 'desc', 'lat', 'lon', 'zone_id', 'url', 'location_type', 'parent_station', 'wheelchair_boarding']}
           }


def insert_gtfs(base: dict):
    base['database'].clear_tables()

    open(base['path'], 'wb').write(requests.get(base['url']).content)
    with zipfile.ZipFile(base['path']) as zip_ref:
        zip_ref.extractall(f"./{base['folder']}/")

    for key, value in base['columns'].items():
        base['database'].insert_data(f"./{base['folder']}/{key}.txt", key, value)

    os.remove(base['path'])


def thread_maj_idf(self):
    guildes = [991054601572724776, 991077146267099166, 991066260164968488, 991066287910322196, 991066318809759784,
               991066347565899786, 991066374216515604, 991066397004161105, 991066423210164224, 991077178529677322,
               1049392301241282641]

    url = 'https://data.iledefrance-mobilites.fr/explore/dataset/arrets-lignes/download/?format=csv&timezone=Europe/Berlin&lang=fr&use_labels_for_header=true&csv_separator=%3B'
    open('./idfm/stops_routes.txt', 'wb').write(requests.get(url).content)

    insert_gtfs(Bases.IDFM.value)

    database = DatabaseIDF()
    for i in guildes:
        guild = self.bot.get_guild(i)
        for emoji in guild.emojis:
            database.add_emoji(emoji.name[5:], f"<:{emoji.name}:{emoji.id}>")

    database.update_cities()


def thread_maj_tan():
    insert_gtfs(Bases.TAN.value)


class Tasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.maj_bdd_gtfs.start()
        print("Module Tasks chargé")

    @tasks.loop(time=datetime.time(hour=7))
    async def maj_bdd_gtfs(self):
        threading.Thread(target=thread_maj_idf, args=(self,)).start()
        threading.Thread(target=thread_maj_tan, args=(self,)).start()

    @tasks.loop(minutes=5)
    async def maj_bdd_tbm(self):
        threading.Thread(target=DatabaseTBM().update(), args=(self,)).start()


async def setup(bot: commands.Bot):
    await bot.add_cog(Tasks(bot))
