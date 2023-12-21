import asyncio
import datetime
import json
import random

import discord
from discord import app_commands
from discord.ext import commands

CONFIG = json.load(open(r"./config.json", "r", encoding="utf-8"))
MY_GUILD = discord.Object(id=326035810338078720)


async def affiche_embed(titre: str, interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(title=titre))
    await asyncio.sleep(3)
    await interaction.delete_original_response()


def embed(interaction: discord.Interaction, valeur: int, raison: str, utilisateur: discord.Member):
    embed_mute = discord.Embed(title="<:mutepushbutton:767788400191078410> | **Demande de mute**", colour=0xFBCD38)
    embed_mute.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar)
    embed_mute.add_field(name="Personne à muter", value=utilisateur.mention)
    embed_mute.add_field(name="Raison", value=raison)
    embed_mute.add_field(name="Votes restants", value=valeur, inline=False)
    return embed_mute


class Mute(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.tree.sync()
        print("Module Mute chargé")

    @app_commands.command(name="mute", description="Mute quelqu'un")
    @app_commands.describe(utilisateur="L'utilisateur à mute")
    @app_commands.describe(duree="La durée du mute en minutes")
    async def mute(self, interaction: discord.Interaction, utilisateur: discord.Member, duree: int):
        if f"id:{interaction.user.id}" in CONFIG['serveurs'][str(interaction.guild_id)]['admins']:
            try:
                await utilisateur.timeout(datetime.timedelta(minutes=duree))
                await affiche_embed(f"<:oui:691282798803157048> | {utilisateur} a été mute pour {duree} minutes",
                                    interaction)
            except Exception as e:
                print(e)
                await affiche_embed("<:non:691282819250651177> | **Permissions insuffisantes pour le bot**",
                                    interaction)
        else:
            await affiche_embed("<:non:691282819250651177> | **Vous n'avez pas le droit de faire cette commande**",
                                interaction)

    @app_commands.command(name="demute", description="Démute quelqu'un")
    @app_commands.describe(utilisateur="L'utilisateur à démute")
    async def unmute(self, interaction: discord.Interaction, utilisateur: discord.Member):
        if f"id:{interaction.user.id}" in CONFIG['serveurs'][str(interaction.guild_id)]['admins']:
            try:
                await affiche_embed(f"<:oui:691282798803157048> | {utilisateur} a été demute", interaction)
                await utilisateur.timeout(datetime.timedelta())
            except Exception as e:
                print(e)
                await affiche_embed("<:non:691282819250651177> | **Permissions insuffisantes pour le bot**",
                                    interaction)
        else:
            await affiche_embed("<:non:691282819250651177> | **Vous n'avez pas le droit de faire cette commande**",
                                interaction)

    @app_commands.command(name="tayeule", description="Mute quelqu'un démocratiquement")
    @app_commands.describe(utilisateur="L'utilisateur à mute")
    @app_commands.describe(raison="La raison qui vous pousse à vouloir le mute")
    async def mute_democratique(self, interaction: discord.Interaction, utilisateur: discord.Member, raison: str):
        t = 0
        pluriel = {1: "minute"}
        demande = self.bot.get_channel(int(CONFIG['demande'][3:]))

        await affiche_embed("<:oui:691282798803157048> | Demande envoyée", interaction)

        if f"id:{utilisateur.id}" in CONFIG['serveurs'][str(interaction.guild_id)]['admins'][:3]:
            guild = self.bot.get_guild(326035810338078720)
            utilisateur = await guild.fetch_member(interaction.user.id)

        votes, des = 10, 1
        if utilisateur.id == 339084574414077954:
            votes, des = 7, 2
        elif "💳 | Carte de fidélité Platinum" in str(utilisateur.roles):
            votes, des = 6, 3
        elif "💳 | Carte de fidélité" in str(utilisateur.roles):
            votes, des = 8, 2

        message = await demande.send(embed=embed(interaction, votes, raison, utilisateur))
        for r in ["<:mutepushbutton:767788400191078410>", "<:nomute:768547426302689320>",
                  "<:muteend:768547490496380968>"]:
            await message.add_reaction(r)

        await self.vote(interaction, message, votes, raison, utilisateur)
        await message.clear_reactions()

        bonus = random.randint(1, 10)
        for loop in range(des):
            t += random.randint(1, 6) * bonus

        await utilisateur.timeout(datetime.timedelta(minutes=t))

        decompte = discord.Embed(title="<:muteend:768547490496380968> | **Mute effectué**", colour=0xFCFCFC)
        for loop in range(t):
            decompte.add_field(name="Personne visée", value=utilisateur.mention, inline=False)
            decompte.add_field(name="Durée initiale", value=f"{t} {pluriel.get(t, 'minutes')}")
            decompte.add_field(name="Durée restante", value=f"{t - loop} {pluriel.get(t - loop, 'minutes')}")
            decompte.add_field(name="Bonus", value=f"x{bonus}")
            await message.edit(embed=decompte)

            await asyncio.sleep(60)

        decompte.remove_field(2)
        await message.edit(embed=decompte)

    async def vote(self, interaction: discord.Interaction, message: discord.Message, votes: int, raison: str,
                   utilisateur: discord.Member):
        def check_emoji(reaction_check):
            return message.id == reaction_check.message.id

        votants, accelere = [], []

        while len(votants) < votes and len(accelere) < 2:
            reaction, user = await self.bot.wait_for('reaction_add', check=check_emoji)
            if "768547426302689320" in str(reaction) and f"id:{user.id}" in \
                    CONFIG['serveurs'][str(interaction.guild_id)]['admins']:
                refus = discord.Embed(title="<:non:691282819250651177> | **Mute refusé**", colour=0xED1C23)
                refus.add_field(name="Personne", value=user.name)
                await message.clear_reactions()
                await message.edit(embed=refus)
                return
            elif "767788400191078410" in str(reaction) and user.name not in votants:
                votants.append(user.name)
                await message.edit(embed=embed(interaction, votes - len(votants), raison, utilisateur))
            elif "768547490496380968" in str(reaction) and f"id:{user.id}" in \
                    CONFIG['serveurs'][str(interaction.guild_id)]['admins'] and (user.name not in accelere):
                accelere.append(user.name)
            else:
                await message.remove_reaction(reaction, user)


async def setup(bot: commands.Bot):
    await bot.add_cog(Mute(bot))
