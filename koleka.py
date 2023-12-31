import asyncio
import json
import os
from random import randint

import discord
from discord.ext import commands

MY_GUILD = discord.Object(id=...)
TOKEN = "..."
bot = commands.Bot(command_prefix='k!', intents=discord.Intents.all(), application_id='...')


@bot.event
async def on_guild_join(guild):
    json_file = open("/home/orelian/Bureau/Bot/config_on_guild_join.json", "r", encoding="utf-8")
    config_on_guild_join = json.load(json_file)

    config_on_guild_join["serveurs"][str(guild.id)] = {"stonks_channel": None, "stonks_message": None, "admins": [f"id:{guild.owner_id}"]}

    with open('/home/orelian/Bureau/Bot/config_on_guild_join.json', 'w') as fp:
        json.dump(config_on_guild_join, fp)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    jeu = [" Koleka Flight Simulator", " Koleka Truck Simulator", " Koleka Cooking Simulator",
           " Koleka Driving School",
           " Koleka For Speed"]
    game = discord.Game(jeu[randint(0, 4)])
    await bot.change_presence(activity=game)


@bot.event
async def on_voice_state_update(member, _, __):
    voice_state = member.guild.voice_client
    if voice_state and len(voice_state.channel.members) == 1:
        await voice_state.disconnect()


async def setup(bot_setup: commands.Bot):
    for file in os.listdir('./cogs'):
        if file.endswith('.py'):
            await bot_setup.load_extension(f'cogs.{file[:-3]}')


asyncio.run(setup(bot))
bot.run(TOKEN)
