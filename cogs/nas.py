import asyncio
import os
import re

import discord
import psutil
import pytube as pytube
from discord import app_commands
from discord.ext import commands

CHARGEMENT = discord.Embed(title='<a:chargement:989320204448313345> | **Chargement ...**')


async def affiche_embed(titre: str, interaction: discord.Interaction) -> None:
    embed = discord.Embed(title=titre)
    await interaction.response.send_message(embed=embed)
    await asyncio.sleep(3)
    await interaction.delete_original_response()


def get_size(bytes_func) -> str:
    """
    Returns size of bytes_func in a nice format
    """
    for unit in ['', 'K', 'M', 'G', 'T', 'P']:
        if bytes_func < 1024:
            return f"{bytes_func:.1f} {unit}o"
        bytes_func /= 1024


async def upload_fichier(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer(ephemeral=False)
    await interaction.followup.send(embed=CHARGEMENT)

    contenu = message.content
    if contenu and "yout" in contenu:
        contenu = re.search("(?P<url>https?://\S+)", contenu).group("url")

        yt = pytube.YouTube(contenu)
        try:
            embed = discord.Embed(title='<a:chargement:989320204448313345> | **Téléchargement ...**')
            await interaction.edit_original_response(embed=embed)
            yt.streams.get_highest_resolution().download(
                    output_path="/mnt/sda5/Orelian/INA/INA/Téléchargements/")
        except Exception as e:
            print(e)
            embed = discord.Embed(title="<:non:691282819250651177> | **Erreur de téléchargement**")
            await interaction.edit_original_response(embed=embed)
            await asyncio.sleep(3)
            await interaction.delete_original_response()
            return

        embed = discord.Embed(title="<:oui:691282798803157048> | **Vidéo téléchargée**")
        await interaction.edit_original_response(embed=embed)
        await asyncio.sleep(3)
        await interaction.delete_original_response()
    else:
        embed = discord.Embed(title="<:non:691282819250651177> | **Il n'y a rien à télécharger**")
        await interaction.edit_original_response(embed=embed)
        await asyncio.sleep(3)
        await interaction.delete_original_response()


class NAS(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(name="Upload à l'INA", callback=upload_fichier)
        self.bot.tree.add_command(self.ctx_menu)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.tree.sync()
        print("Module NAS chargé")

    @app_commands.command(name="ina", description="État de l'INA")
    async def ina(self, interaction: discord.Interaction):
        disque = psutil.disk_usage("/mnt/sda5/")
        ram = psutil.virtual_memory()
        embed = discord.Embed(title="<:ina:1078753867648466994> | Statistiques", colour=0x028CB5)
        embed.add_field(name="Disque",
                        value=f'{get_size(disque.used)} / {get_size(disque.total)} | {disque.percent} % utilisés')
        embed.add_field(name="CPU",
                        value=f'{psutil.cpu_percent()} %, {psutil.sensors_temperatures()["coretemp"][0].current}°C',
                        inline=False)
        embed.add_field(name="RAM",
                        value=f'{get_size(ram.used)} / {get_size(ram.total)} | {ram.percent} % utilisés',
                        inline=False)
        embed.add_field(name="Réseau", value="<a:chargement:989320204448313345> | **Chargement ...**",
                        inline=False)
        await interaction.response.send_message(embed=embed)

        io = psutil.net_io_counters()
        await asyncio.sleep(10)
        io_2 = psutil.net_io_counters()
        us, ds = io_2.bytes_sent - io.bytes_sent, io_2.bytes_recv - io.bytes_recv

        embed.set_field_at(3, name="Réseau",
                           value=f'⭱ {get_size(us / 10)}/s | ⭳ {get_size(ds / 10)}/s',
                           inline=False)
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="redemarre", description="Redémarrer l'INA")
    async def redemarre(self, interaction: discord.Interaction):
        if interaction.user.id != 215787907984785410:
            await affiche_embed("<:non:691282819250651177> | **Vous n'avez pas le droit de faire cette commande**",
                                interaction)
            return

        await affiche_embed("<:oui:691282798803157048> | L'INA redémarre...", interaction)
        os.system('reboot')

    @app_commands.command(name="demarre", description="Démarrer certaines tâches de l'INA")
    @app_commands.describe(tache="La tâche à démarrer")
    @app_commands.choices(tache=[
        app_commands.Choice(name="Minecraft", value="minecraft"),
        app_commands.Choice(name="Teamviewer", value="team"),
        app_commands.Choice(name="Bot", value="bot")
    ])
    async def demarre(self, interaction: discord.Interaction, tache: app_commands.Choice[str]):
        if interaction.user.id != 215787907984785410:
            await affiche_embed("<:non:691282819250651177> | **Vous n'avez pas le droit de faire cette commande**",
                                interaction)
            return

        match tache.value:
            case "ets2":
                os.system(
                        "gnome-terminal -- sh -c 'cd \"/home/orelian/.local/share/Steam/steamapps/common/Euro Truck Simulator 2 Dedicated Server/bin/linux_x64/\";./server_launch.sh'")
            case "minecraft":
                os.system("gnome-terminal -- sh -c 'cd /home/orelian/Bureau/Serveur/Minecraft/;./start.sh'")
            case "team":
                os.system("/opt/teamviewer/tv_bin/script/teamviewer")
            case "bot":
                await affiche_embed("<:oui:691282798803157048> | La tâche démarre...", interaction)
                os.system("gnome-terminal -- sh -c 'python3 ./koleka.py'")
                # cp -fr /mnt/sda5/Bot/* ~/Bureau/Serveur/Bot;
                await self.bot.close()
        await affiche_embed("<:oui:691282798803157048> | La tâche démarre...", interaction)

    @app_commands.command(name="partage", description="Créer un lien de partage depuis l'INA")
    @app_commands.describe(chemin="Chemin du fichier depuis la racine")
    async def partage(self, interaction: discord.Interaction, chemin: str):
        if interaction.user.id != 215787907984785410:
            await affiche_embed("<:non:691282819250651177> | **Vous n'avez pas le droit de faire cette commande**",
                                interaction)
            return

        command = f'ln -s "/mnt/sda5/INA/{chemin}" "/var/www/html/"'
        p = os.system('echo %s|sudo -S %s' % ('0077386', command))
        if p:
            await affiche_embed("<:non:691282819250651177> | **Le chemin est incorrect**", interaction)
        else:
            await affiche_embed(
                    f"<:oui:691282798803157048> | **https://mustafic.freeboxos.fr/{chemin.rsplit('/', 1)[-1]}/**",
                    interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(NAS(bot))
