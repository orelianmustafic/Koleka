import asyncio
import re
from enum import Enum
from typing import Optional

import discord
import requests
from discord import app_commands
from discord.app_commands import Group
from discord.ext import commands
from discord.ui import Select, View

from database.database import Database
from database.database_idf import DatabaseIDF
from database.database_tan import DatabaseTAN
from database.database_tbm import DatabaseTBM
from database.database_users import DatabaseUsers
from horaire.station import Station
from horaire.station_idf import StationIDF
from horaire.station_tan import StationTAN
from horaire.station_tbm import StationTBM

IDFM_INDISPONIBILITE = "<:non:691282819250651177> | **Indisponibilité des données fournies**"
CHIFFRES = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
LIGNES = [["A", "B", "C", "D", "E"],
          ["H", "J", "K", "L", "N", "P", "R", "U"],
          ["1", "2", "3", "3B", "4", "5", "6", "7", "7B", "8", "9", "10", "11", "12", "13", "14"],
          ["T1", "T2", "T3a", "T3b", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T13"]]


class Reseau:
    def __init__(self, nom: str, station: type[Station], database: Database):
        self.nom = nom
        self.station = station
        self.database = database


class Reseaux(Enum):
    IDFM = Reseau('Île-de-France', StationIDF, DatabaseIDF())
    TBM = Reseau('Bordeaux', StationTBM, DatabaseTBM())
    TAN = Reseau('Nantes', StationTAN, DatabaseTAN())

    @classmethod
    def choices(cls):
        return [app_commands.Choice(name=reseau.value.nom, value=reseau.name) for reseau in cls]

    @classmethod
    def nom(cls, reseau: str) -> str:
        return cls[reseau].value.nom

    @classmethod
    def station(cls, reseau: str, arret: str) -> Station:
        return cls[reseau].value.station(arret)

    @classmethod
    def database(cls, reseau: str) -> Database:
        return cls[reseau].value.database


async def affiche_embed(interaction: discord.Interaction, titre: str) -> None:
    """Affiche un embed"""
    embed = embed_ratp(titre)
    await interaction.edit_original_response(embed=embed)
    await asyncio.sleep(3)
    await interaction.delete_original_response()


async def chargement(interaction: discord.Interaction) -> None:
    """Affiche un embed de chargement"""
    await interaction.response.send_message(embed=embed_ratp("<a:chargement:989320204448313345> | **Chargement ...**"))


def embed_ratp(description=None, couleur=0x2F3136) -> discord.Embed:
    """Retourne un embed de type RATK (même titre ; description et couleurs pouvant être choisies)
    :return: Embed avec emoji RATK, la description et la couleur données
    """
    return discord.Embed(title="<:ratk:697886113196671058> | **Horaires**",
                         description=description,
                         color=couleur)


async def station_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Retourne une liste des choix correspondant à la frappe de l'utilisateur

    :param interaction: Interaction discord associée
    :param current: Champ que l'utilisateur est en train de saisir
    :return: Liste de choix possibles correspondant à ce que l'utilisateur a entré
    """
    database = Reseaux.database(interaction.data['options'][0]['options'][0]['value'])

    if not current:
        stations = DatabaseUsers().get_favoris(interaction.user)
        stations_noms = [database.get_nom_arret(i) for i in stations]
        stations = [i + "_" for i in stations]
    else:
        stations = database.get_arrets(current)
        stations_noms = [f"{arret[2]}, {arret[14]}" if arret[14] else arret[2] for arret in stations]
        stations = [i[0] + "_" for i in stations]

    return [
        app_commands.Choice(name=station, value=stations[i])
        for i, station in enumerate(stations_noms) if current.lower() in station.lower()
    ]


def get_info_trafic() -> dict:
    """Obtient l'info trafic

    :return: Dictionnaire contentant pour chaque ligne une liste des messages d'info trafic
    """
    database = DatabaseIDF()

    url = 'https://prim.iledefrance-mobilites.fr/marketplace/general-message'
    headers = {'Accept': 'application/json', 'apikey': 'UMLKyEXZt8isAm4jt5zBGqsdONr30650'}
    params = {'LineRef': 'ALL', 'InfoChannelRef': 'Perturbation'}
    try:
        requete = requests.get(url, headers=headers, params=params).json()
    except requests.RequestException:
        raise requests.RequestException

    requete = requete['Siri']['ServiceDelivery']['GeneralMessageDelivery'][0]['InfoMessage']

    _dict = {}
    for i in requete:
        entreprises = ["IDFM:71", "IDFM:1046", "IDFM:Operator_100"]
        ligne = ''

        if "LineRef" not in i["Content"]:
            x = re.search(r"[&,. ][ABCDEHJKLNPRU][&,. ]|RER[ABCDEHJKLNPRU]",
                          i["Content"]["Message"][0]["MessageText"]["value"])
            if x and i["Content"]["Message"][0]["MessageText"]["lang"].lower() == "fr":
                ligne = re.sub("[&,. ]|RER", '', x.group())
                ligne = database.get_nom_ligne(database.get_ligne(ligne)[0])
        elif database.get_agency(i["Content"]["LineRef"][0]['value']) in entreprises:
            ligne = database.get_nom_ligne(i["Content"]["LineRef"][0]['value'])

        if any(ligne in sublist for sublist in LIGNES):
            if str(ligne) not in _dict:
                _dict[str(ligne)] = []
            _dict[str(ligne)].append(i["Content"]["Message"][0]["MessageText"]["value"])

    return _dict


def embed_info_trafic(_dict: dict, num_page: int, ligne: str) -> discord.Embed:
    """Crée un embed d'info trafic

    :param _dict: Dictionnaire de lignes et leurs messages d'info trafic [get_info_trafic()]
    :param num_page: Numéro de la page souhaitée
    :param ligne: Identifiant de la ligne
    :return: Embed d'info trafic
    """
    database = DatabaseIDF()
    etats = ['🟢 | Trafic normal', '🟡 | Travaux', '🟠 | Perturbé', '🔴 | Interrompu']
    embed = discord.Embed(title="<:ratk:697886113196671058> | **Info trafic**")

    iterateur = LIGNES[num_page]
    if ligne:
        iterateur = [ligne]

    status = [set(), set(), set(), set()]
    for i in iterateur:
        if i not in _dict:
            status[0].add(i)
            continue
        for message in _dict[i]:
            if ('interrompu' in message and not [ele for ele in ['travaux', 'Tvx'] if
                                                 (ele.casefold() in message.casefold())]
                and not re.search("\d{1,2}h\d{0,2}", message)) or (
                    'interrompu'.casefold() in message.casefold() and 'reprise'.casefold() in message.casefold()):
                status[3].add(i)
            elif not [ele for ele in ['travaux', 'Tvx'] if
                      (ele.casefold() in message.casefold())] and not re.search(
                    "\d{1,2}h\d{0,2}", message):
                status[2].add(i)
            else:
                status[1].add(i)

    status[1] = status[1].difference(status[3])
    status[1] = status[1].difference(status[2])
    status[2] = status[2].difference(status[3])

    status = [sorted(i) for i in status]
    for i, e in enumerate(status):
        if e:
            embed.add_field(name=etats[i],
                            value='  '.join([database.get_emoji(database.get_ligne(i)[0]) for i in e]),
                            inline=False)

    return embed


async def messages_info_trafic(interaction: discord.Interaction, _dict: dict, num_page: int, ligne: str):
    """Gestion d'embed des messages info trafic

    :param interaction: Interaction discord associée
    :param _dict: Dictionnaire de lignes et leurs messages d'info trafic [get_info_trafic()]
    :param num_page: Numéro de la page
    :param ligne: Identifiant de la ligne
    """
    embed: discord.Embed = embed_info_trafic(_dict, num_page, ligne)
    embed.add_field(name='Messages', value=' ')
    database = DatabaseIDF()

    if ligne:
        _dict = {k: sorted(_dict[k]) for k in _dict.keys() & [ligne]}
    else:
        _dict = {k: sorted(_dict[k]) for k in _dict.keys() & LIGNES[num_page]}
    longeur = sum(len(v) for v in _dict.values())

    while True:
        compteur = 1
        for i, e in _dict.items():
            if not _dict.items():
                await asyncio.sleep(5000)
            for f in e:
                embed.set_field_at(-1, name='Messages',
                                   value=database.get_emoji(database.get_ligne(i)[0]) + ' ' + f)
                embed.set_footer(text=f'Message {compteur}/{longeur}')
                await interaction.edit_original_response(embed=embed)
                await asyncio.sleep(len(f) / 15)
                compteur += 1


class IDFM(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.tree.sync()
        print("Module Transport chargé")

    async def choix_ville(self, arrets_choix: list, interaction_choix: discord.Interaction) -> int:
        select = Select()

        for i, arret in enumerate(arrets_choix):
            print(arret[14])
            select.append_option(discord.SelectOption(value=str(i),
                                                      label=f"{arret[2]}, {arret[14]}" if arret[14] else arret[2]))

        await interaction_choix.edit_original_response(view=View().add_item(select))
        await self.bot.wait_for('interaction')

        return int(select.values[0])

    async def initialiser_arret(self, interaction: discord.Interaction, arret: str, database: Database) -> str | None:
        if "_" in arret:
            return arret[:-1]

        arrets = database.get_arrets(arret)

        similarites = [i[-1] for i in arrets if i[-1] >= 90]

        if not arrets or arrets[0][-1] <= 60:  # S'il n'y a aucune station trouvée
            return None
        elif len(similarites) == 1:  # Si il n'y a qu'une correspondance
            arret = arrets[0][0]
        elif len(similarites) > 1:  # Si on a plus d'une correspondance
            arret = arrets[await self.choix_ville([i for i in arrets if i[-1] >= 90], interaction)][0]
        else:  # Sinon affiche toutes les correspondances au-dessus de 60 %
            arret = arrets[await self.choix_ville([i for i in arrets if i[-1] >= 60], interaction)][0]

        return arret

    g_horaires = Group(name='horaires', description='description')
    g_favoris = Group(parent=g_horaires, name='favori', description='description')

    @g_horaires.command(name="chercher", description="Horaires du réseau francilien")
    @app_commands.choices(reseau=Reseaux.choices())
    @app_commands.autocomplete(arret=station_autocomplete)
    @app_commands.describe(arret="Nom de l'arrêt")
    @app_commands.describe(ligne="Ligne voulue (optionnel)")
    async def horaires(self, interaction: discord.Interaction, reseau: app_commands.Choice[str], arret: str, ligne: Optional[str]):
        await chargement(interaction)

        reseau = reseau.value
        arret = await self.initialiser_arret(interaction, arret, Reseaux.database(reseau))

        if not arret:
            await affiche_embed(interaction, "<:non:691282819250651177> | **Station non trouvée**")

        # Si il y a des problèmes au niveau de l'API
        try:
            station: Station = Reseaux.station(reseau, arret)
        except Exception as e:
            print(e)
            await affiche_embed(interaction, "<:non:691282819250651177> | **Données indisponibles**")
            return

        # S'il n'y a aucun départ à la station
        if not station.lignes:
            await affiche_embed(interaction, "<:non:691282819250651177> | **Aucun départ**")
            return

        # Si l'utilisateur a fourni une ligne spécifique, on cherche le numéro de page correspondant à cette ligne
        num_page = station.get_index_ligne(ligne)

        vue = BoutonsHoraires(interaction, reseau, station, num_page)
        await interaction.edit_original_response(embed=vue.panneau(), view=vue)

    '''@app_commands.command(name="test", description="Oui")
    async def test(self, interaction: discord.Interaction):
        emojis = {
            'bif': "<:bif_gauche:1128344288791646228><:bif_droite:1128344285813682318>",
            'suite_haut': "<:suite_haut:1015018503243313232>",
            'suite_bas': "<:suite_bas:1119977954747875410>",
            'vide': "<:vide:821807321302040617>",
            'terminus_haut': "<:terminus_haut:1076645446564446209>",
            'terminus_bas': "<:terminus_bas:1015018500026273872>",
            'arret': "<:arret:1076955735218458816>",
            'non_desservi': "<:arret_non_desservi:1077985563065462917>",
            'route': "<:route:1015018508221956137>",
            'bus': "🚍"
        }

        desc = ""
        branches = 2

        tronc = 3
        branche_1 = 5
        branche_2 = 4

        desc += emojis['suite_haut'] + emojis['vide'] * branches + '\n'
        for _ in range(branche_1):
            desc += emojis['arret'] + emojis['vide'] * branches + '\n'
        desc += emojis['route'] + emojis['terminus_haut'] + emojis['vide'] + '\n'

        for _ in range(branche_2):
            desc += emojis['route'] + emojis['arret'] + emojis['vide'] + '\n'
        desc += emojis['bif'] + "\n"

        for _ in range(tronc):
            desc += emojis['arret'] + emojis['vide'] * branches + '\n'
        desc += emojis['terminus_bas'] + emojis['vide'] * branches + '\n'

        embed = discord.Embed(title="<:ratk:697886113196671058> | **Horaires**",
                              description=desc)

        await interaction.response.send_message(embed=embed)'''

    @g_horaires.command(name="info", description="Info trafic du réseau francilien (expérimental !)")
    @app_commands.describe(ligne="Ligne voulue (optionnel)")
    async def info_trafic(self, interaction: discord.Interaction, ligne: Optional[str] = None):
        def check_emoji(reaction_check, user_check) -> bool:
            """Vérifie si l'émoji est bien lié au message"""
            return message.id == reaction_check.message.id and message.interaction.user.id == user_check.id

        await chargement(interaction)
        message = await interaction.original_response()

        try:
            info_trafic = get_info_trafic()
        except Exception as e:
            print(e)
            await interaction.response.send_message(embed=embed_ratp(IDFM_INDISPONIBILITE))
            return

        database = DatabaseIDF()
        num_page = 0
        emotes = ["⬅️", "➡️", "🔄"]
        if ligne:
            if not database.get_ligne(ligne):
                await interaction.edit_original_response(
                        embed=embed_ratp("<:non:691282819250651177> | **Ligne inconnue**"))
                return
            emotes = ["🔄"]

        for i in emotes:
            await message.add_reaction(i)

        while True:
            await interaction.edit_original_response(embed=embed_info_trafic(info_trafic, num_page, ligne))
            message = await interaction.original_response()

            done, pending = await asyncio.wait([
                asyncio.create_task(self.bot.wait_for('reaction_add', check=check_emoji)),
                asyncio.create_task(messages_info_trafic(interaction, info_trafic, num_page, ligne))
            ], return_when=asyncio.FIRST_COMPLETED)

            for task in pending:
                task.cancel()

            reaction, user = done.pop().result()
            await message.remove_reaction(reaction, user)

            match str(reaction):
                case "⬅️":
                    num_page = (num_page - 1) % len(LIGNES)
                case "➡️":
                    num_page = (num_page + 1) % len(LIGNES)
                case "🔄":
                    try:
                        info_trafic = get_info_trafic()
                    except Exception as e:
                        print(e)
                        await interaction.edit_original_response(embed=embed_ratp(IDFM_INDISPONIBILITE))
                        return
                    await interaction.edit_original_response(embed=embed_info_trafic(info_trafic, num_page, ligne))
                    message = await interaction.original_response()

    @g_favoris.command(name="ajouter", description="Enregistrer les stations favorites")
    @app_commands.choices(reseau=Reseaux.choices())
    @app_commands.autocomplete(arret=station_autocomplete)
    @app_commands.describe(arret="Nom de l'arrêt")
    async def enregistrer_favori(self, interaction: discord.Interaction, reseau: app_commands.Choice[str], arret: str):
        await chargement(interaction)

        reseau = reseau.value
        arret = await self.initialiser_arret(interaction, arret, Reseaux.database(reseau))

        if not arret:
            await affiche_embed(interaction, "<:non:691282819250651177> | **Station non trouvée**")
            return

        try:
            DatabaseUsers().add_favori(interaction.user, arret)
        except Exception as e:
            print(e)
            await affiche_embed(interaction, "**<:non:691282819250651177> | Favori déjà ajouté**")
            return

        await interaction.edit_original_response(embed=embed_ratp("**<:oui:691282798803157048> | Favori ajouté**"))

    @g_favoris.command(name="supprimer", description="Supprimer une station favorite")
    @app_commands.choices(reseau=Reseaux.choices())
    @app_commands.autocomplete(arret=station_autocomplete)
    @app_commands.describe(arret="Nom de l'arrêt")
    async def supprimer_favori(self, interaction: discord.Interaction, reseau: app_commands.Choice[str], arret: str):
        await chargement(interaction)

        DatabaseUsers().remove_favori(interaction.user, arret)
        try:
            await affiche_embed(interaction, "**<:oui:691282798803157048> | Favori supprimé**")
        except Exception as e:
            print(e)
            await affiche_embed(interaction, "**<:non:691282819250651177> | Favori invalide ou non existant**")

    @g_favoris.command(name="liste", description="Voir votre liste de stations favorites")
    async def voir_favori(self, interaction: discord.Interaction):
        await chargement(interaction)

        favoris = DatabaseUsers().get_favoris(interaction.user)
        favoris = [f' • {DatabaseIDF().get_nom_arret(i)} \n' for i in favoris]
        await interaction.edit_original_response(embed=embed_ratp(''.join(favoris)))


class Boutons(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, reseau: str, station: Station, num_page: int):
        super().__init__(timeout=1200)
        self.interaction = interaction
        self.reseau = reseau
        self.station = station
        self.num_page = num_page
        self.num_direction = 0


class BoutonsHoraires(Boutons):
    def __init__(self, interaction: discord.Interaction, reseau: str, station: Station, num_page: int):
        super().__init__(interaction, reseau, station, num_page)

    def panneau(self) -> discord.Embed:
        """Fournit un embed montrant le temps d'attente pour un arrêt et une station donnée"""
        ligne = self.station.get_ligne(self.num_page)

        ratp = discord.Embed(title=f"{ligne.emoji} | **Horaires**",
                             color=ligne.couleur)
        ratp.set_footer(text=f'Page {self.num_page + 1}/{len(self.station.lignes)}')

        for arret in ligne.arrets:
            if f"**{arret.nom or self.station.nom}**" not in [x.value for x in ratp.fields]:
                ratp.add_field(name="‎", value=f"**{arret.nom}**", inline=False)

            horaires = arret.horaires.items()
            horaires_inline = True if (len(horaires) < 2) else False

            for destination, temps in horaires:
                temps = [i for i in temps[:3] if i <= 60]
                if not temps:
                    continue
                elif f"**{arret.nom}**" not in [x.value for x in ratp.fields]:
                    ratp.add_field(name=f"→ {destination}", value=" min, ".join(map(str, temps)) + " min",
                                   inline=horaires_inline)
                else:
                    ratp.insert_field_at([x.value for x in ratp.fields].index(f"**{arret.nom}**") + 1,
                                         name=f"→ {destination}", value=" min, ".join(map(str, temps)) + " min",
                                         inline=horaires_inline)

        if len(ratp.fields) < 2:
            ratp.add_field(name="Aucun départ", value="...")

        return ratp

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.gray)
    async def page_precedente(self, interaction: discord.Interaction, __: discord.ui.Button):
        self.num_page = (self.num_page - 1) % len(self.station.lignes)
        await self.rafraichir(interaction)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.grey)
    async def page_suivante(self, interaction: discord.Interaction, __: discord.ui.Button):
        self.num_page = (self.num_page + 1) % len(self.station.lignes)
        await self.rafraichir(interaction)

    @discord.ui.button(emoji="🔄", style=discord.ButtonStyle.grey)
    async def recharger(self, interaction: discord.Interaction, __: discord.ui.Button):
        self.station.rafraichir()
        await self.rafraichir(interaction)

    @discord.ui.button(emoji="📍", style=discord.ButtonStyle.grey)
    async def localisation(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.defer()
        self.station.rafraichir()
        try:
            vue = BoutonsLocalisation(interaction, self.reseau, self.station, self.num_page)
            await interaction.edit_original_response(embed=vue.panneau_ligne(), view=vue)
        except Exception as e:
            print(e)
            await interaction.edit_original_response(embed=embed_ratp(
                    "<:non:691282819250651177> | **Localisation des véhicules impossible sur cette ligne**"))
            await asyncio.sleep(3)
            await interaction.edit_original_response(embed=self.panneau())

    async def rafraichir(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(embed=self.panneau())

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        await self.interaction.edit_original_response(view=self)


class BoutonsLocalisation(Boutons):
    def __init__(self, interaction: discord.Interaction, reseau: str, station: Station, num_page: int):
        super().__init__(interaction, reseau, station, num_page)
        self.routes = self.station.get_journey(self.station.id,
                                               self.station.get_ligne(self.num_page).id)
        self.max_directions = len(self.routes)

    def panneau_ligne(self) -> discord.Embed:
        """Fournit un embed décrivant la position théorique des véhicules sur les 5 deniers arrêts"""
        emojis = {
            'bif': "<:bif_gauche:1128344288791646228><:bif_droite:1128344285813682318>",
            'suite_haut': "<:suite_haut:1015018503243313232>",
            'suite_bas': "<:suite_bas:1119977954747875410>",
            'vide': "<:vide:821807321302040617>",
            'terminus_haut': "<:terminus_haut:1076645446564446209>",
            'terminus_bas': "<:terminus_bas:1015018500026273872>",
            'arret': "<:arret:1076955735218458816>",
            'non_desservi': "<:arret_non_desservi:1077985563065462917>",
            'route': "<:route:1015018508221956137>",
            'bus': "🚍"
        }

        desc = ""
        nouveau_attente = float('inf')
        route = self.routes[self.num_direction][-6:]

        if not route:
            self.num_direction = (self.num_direction + 1) % len(self.num_direction)
            route = self.routes[self.num_direction][-6:]
        if route[0][1] > 0:
            desc += emojis['suite_haut'] + emojis['vide'] + ' \n'
            route = route[0:]
        for num_arret, arret in enumerate(route):
            desc2 = ""
            desc3 = ""
            nouveau_url = Reseaux.station(self.reseau, arret[0])
            nom_arret = nouveau_url.nom

            if not nouveau_url:
                desc += emojis['non_desservi'] + emojis['vide'] + '   ' + nom_arret + ' \n'
                if num_arret == len(route) - 1:
                    desc += emojis['suite_bas'] + emojis['vide']
                continue
            if arret[1] == 0:  # Si l'arrêt est le premier de la ligne
                desc += emojis['terminus_haut'] + emojis['bus'] + '   ' + nom_arret + ' \n'
                if num_arret == len(route) - 1:
                    desc += emojis['suite_bas'] + emojis['vide']
                continue

            if num_arret == len(route) - 1:  # Et que c'est notre arrêt
                desc2 += emojis['terminus_bas']
            else:  # Sinon c'est un arrêt normal (avant le nôtre)
                desc2 += emojis['arret']
            desc3 += emojis['vide']

            try:
                attentes = list(nouveau_url.get_ligne().get_arret().horaires.values())
                attentes = attentes[0]
            except (IndexError, AttributeError):
                desc += emojis['non_desservi'] + emojis['vide'] + '   ' + nom_arret + ' \n'
                if num_arret == len(route) - 1:
                    desc += emojis['suite_bas'] + emojis['vide']
                continue
            for attente in attentes:
                # Si ce temps est supérieur au précédent temps, ne pas prendre en compte
                if arret[2] > attente > nouveau_attente:
                    continue
                if 0 < attente < arret[2]:
                    desc += emojis['route'] + emojis['bus']
                    desc += '\n'
                # Si le temps d'attente à l'arrêt est nul
                elif attente == 0:
                    desc2 += emojis['bus']
                    desc3 = ""
                elif nouveau_attente > attente > 0 and num_arret == 0 and arret[1] != 0:
                    desc += emojis['route'] + emojis['bus'] + f' **{attente} min**' + '\n'
                nouveau_attente = attente

            desc += desc2 + desc3
            desc += '   ' + nom_arret + '\n'

        embed = discord.Embed(title="<:ratk:697886113196671058> | **Horaires**",
                              description=desc,
                              color=self.station.get_ligne(self.num_page).couleur)
        embed.set_footer(text=f"Page {self.num_direction + 1}/{self.max_directions}")

        return embed

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.gray)
    async def page_precedente(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.num_direction = (self.num_direction - 1) % self.max_directions
        await self.rafraichir(interaction)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.grey)
    async def page_suivante(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.num_direction = (self.num_direction + 1) % self.max_directions
        await self.rafraichir(interaction)

    @discord.ui.button(emoji="🔄", style=discord.ButtonStyle.grey)
    async def recharger(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.station.rafraichir()
        await self.rafraichir(interaction)

    @discord.ui.button(emoji="↩️", style=discord.ButtonStyle.gray)
    async def en_arriere(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.defer()
        vue = BoutonsHoraires(interaction, self.reseau, self.station, self.num_page)
        await interaction.edit_original_response(embed=vue.panneau(), view=vue)

    async def rafraichir(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(embed=self.panneau_ligne())

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        await self.interaction.edit_original_response(view=self)


class BoutonsInfoTrafic(discord.ui.View):
    def __init__(self):
        super().__init__()


async def setup(bot: commands.Bot):
    await bot.add_cog(IDFM(bot))
