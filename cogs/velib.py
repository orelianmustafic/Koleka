import discord
import typing
from discord import app_commands
from discord.app_commands import Group
from discord.ext import commands

from database.database_velib import DatabaseVelib


async def station_autocomplete(_: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    stations = DatabaseVelib().get_stations(current)

    stations_noms = [i[1] for i in stations]
    stations = [i[0] for i in stations]

    print(stations_noms, stations)

    return [
        app_commands.Choice(name=station, value=stations[i])
        for i, station in enumerate(stations_noms)
    ]


class Velib(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.tree.sync()
        print("Module Vélib' chargé")

    g_velib = Group(name='velib', description='description')

    @g_velib.command(name='chercher', description="Status d'une station Vélib'")
    @app_commands.autocomplete(station=station_autocomplete)
    @app_commands.describe(station="Nom de la station")
    async def velib(self, interaction: discord.Interaction, station: str):
        raise NotImplementedError()


async def setup(bot: commands.Bot):
    await bot.add_cog(Velib(bot))
