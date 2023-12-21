import asyncio

import discord
import yt_dlp
from discord import FFmpegPCMAudio, app_commands
from discord.ext import commands
from discord.utils import get

ERREUR = discord.Embed(title="<:non:691282819250651177> | **Erreur**")
CHARGEMENT = discord.Embed(title='<a:chargement:989320204448313345> | **Chargement ...**')
NON_CONNECTE = "<:non:691282819250651177> | Le client n'est pas connecté au vocal"


async def affiche_embed(titre: str, interaction: discord.Interaction) -> None:
    embed = discord.Embed(title=titre)
    await interaction.response.send_message(embed=embed)
    await asyncio.sleep(3)
    await interaction.delete_original_response()


class Musique(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.tree.sync()
        print("Module Musique chargé")

    @app_commands.command(name="play", description="Jouer de la musique en vocal")
    @app_commands.describe(url="Le lien de la musique à jouer")
    async def play(self, interaction: discord.Interaction, url: str) -> None:
        await interaction.response.send_message(embed=CHARGEMENT)

        if interaction.user.voice:
            channel = interaction.user.voice.channel
        else:
            await interaction.response.send_message(embed=ERREUR)
            return
        voice = get(self.bot.voice_clients, guild=interaction.guild)
        if voice and voice.is_connected():
            await voice.move_to(channel)
        else:
            await channel.connect()

        ydl_options = {'format': 'bestaudio',
                       'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', }], }
        ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                          'options': '-vn'}

        voice = get(self.bot.voice_clients, guild=interaction.guild)

        if not voice.is_playing():
            url2 = None
            with yt_dlp.YoutubeDL(ydl_options) as ydl:
                info = ydl.extract_info(url, download=False)
                if info is not None:
                    url2 = info['url']
            if url2 is not None and voice is not None:
                voice.play(FFmpegPCMAudio(source=url2, executable="/usr/bin/ffmpeg", **ffmpeg_options))
                voice.is_playing()

                embed = discord.Embed(title="<:oui:691282798803157048> | La vidéo va commencer")
                await interaction.edit_original_response(embed=embed)
            await asyncio.sleep(3)
            await interaction.delete_original_response()

    @app_commands.command(name="reprendre", description="Reprendre la musique")
    async def resume(self, interaction: discord.Interaction):
        try:
            voice = get(self.bot.voice_clients, guild=interaction.guild)

            if voice is None:
                await affiche_embed(NON_CONNECTE, interaction)
            elif not voice.is_playing():
                voice.resume()
                await affiche_embed("<:oui:691282798803157048> | Musique reprise", interaction)
            else:
                await affiche_embed("<:non:691282819250651177> | **La musique n'est pas en pause**", interaction)

        except Exception as e:
            print(e)
            await interaction.edit_original_response(embed=ERREUR)
            await asyncio.sleep(3)
            await interaction.delete_original_response()

    @app_commands.command(name="skip", description="Skip la musique")
    async def skip(self, interaction: discord.Interaction):
        try:
            voice = get(self.bot.voice_clients, guild=interaction.guild)

            if voice is None:
                await affiche_embed(NON_CONNECTE, interaction)
            elif voice.is_playing():
                voice.stop()
                await affiche_embed("<:oui:691282798803157048> | Musique skipée", interaction)
            else:
                await affiche_embed(NON_CONNECTE, interaction)

        except Exception as e:
            print(e)
            await interaction.edit_original_response(embed=ERREUR)
            await asyncio.sleep(3)
            await interaction.delete_original_response()

    @app_commands.command(name="pause", description="Mettre en pause la musique")
    async def pause(self, interaction: discord.Interaction):
        try:
            voice = get(self.bot.voice_clients, guild=interaction.guild)

            if voice is None:
                await affiche_embed(NON_CONNECTE, interaction)
            elif voice.is_playing():
                voice.pause()
                await affiche_embed("<:oui:691282798803157048> | Musique mise en pause", interaction)
            else:
                await affiche_embed("<:non:691282819250651177> | **Il n'y a pas de musique en cours de lecture**", interaction)

        except Exception as e:
            print(e)
            await interaction.edit_original_response(embed=ERREUR)
            await asyncio.sleep(3)
            await interaction.delete_original_response()

    @app_commands.command(name="stop", description="Arrêter la musique")
    async def stop(self, interaction: discord.Interaction):
        try:
            voice = get(self.bot.voice_clients, guild=interaction.guild)

            if voice is None:
                await affiche_embed(NON_CONNECTE, interaction)
            elif voice.is_playing():
                voice.stop()
                await voice.disconnect(force=False)
                await affiche_embed("<:oui:691282798803157048> | Musique arrêtée", interaction)
            else:
                await affiche_embed(NON_CONNECTE, interaction)

        except Exception as e:
            print(e)
            await interaction.edit_original_response(embed=ERREUR)
            await asyncio.sleep(3)
            await interaction.delete_original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(Musique(bot))
