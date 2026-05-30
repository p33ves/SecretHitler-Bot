import random
from dataclasses import dataclass
from enum import Enum

import discord

from static_data import colours, images


@dataclass(frozen=True)
class PartyInfo:
    name: str
    image_path: str
    colour: str


class Role(Enum):
    Hitler = 1
    Fascist = 2
    Liberal = 3

    def getRolePic(self) -> str:
        rolePics = {
            1: images["role.png"]["Hitler"],
            2: random.choice(images["role.png"]["Fascist"]),
            3: random.choice(images["role.png"]["Liberal"]),
        }
        return rolePics[self.value]

    def getParty(self) -> PartyInfo:
        if self == Role.Liberal:
            return PartyInfo(self.name, images["party.png"]["Liberal"], "DARK_BLUE")
        return PartyInfo(Role.Fascist.name, images["party.png"]["Fascist"], "RED")


class Player:
    def __init__(self, user):
        self.__user = user
        self.__role = None
        self.__isDead = False

    @property
    def id(self) -> str:
        return self.__user.id

    @property
    def name(self) -> str:
        # TODO If same palyer names join the same game, need to change this into full_name
        return self.__user.name

    @property
    def avatar_url(self) -> str:
        return self.__user.display_avatar.url

    @property
    def isDead(self):
        return self.__isDead

    def kill(self):
        self.__isDead = True

    def setRole(self, role: Role):
        self.__role = role

    async def sendRole(self, count: int, fascists: dict, hitler: namedtuple):
        if self.__role == Role.Liberal:
            desc = "For justice, liberty and equality!"
            col = "BLUE"
        elif self.__role == Role.Fascist:
            col = "ORANGE"
            if count < 7:
                desc = f"Hitler is ***{hitler.name}***"
            elif count < 9:
                desc = f"Your fellow fascist is *{[val for key, val in fascists.items() if key != self.id]}*, Hitler is ***{hitler.name}***"
            else:
                desc = f"Your fellow fascists are *{[val for key, val in fascists.items() if key != self.id]}*, Hitler is ***{hitler.name}***"
        else:
            col = "DARK_ORANGE"
            if count < 7:
                desc = f"*{list(fascists.values())[0]}* is the fascist"
            else:
                desc = "You don't know who the other fascists are!"
        roleEmbed = discord.Embed(
            title=f"You are ***{self.__role.name}***",
            colour=colours[col],
            description=desc,
        )
        file_embed = discord.File(
            self.__role.getRolePic(), filename="role.png")
        roleEmbed.set_author(name=self.name, icon_url=self.avatar_url)
        roleEmbed.set_image(url="attachment://role.png")
        await self.send(file_embed, roleEmbed)

    async def revealParty(self, president):
        party = self.__role.getParty()
        partyEmbed = discord.Embed(
            title=f"{self.name} is from ***{party.name}*** party",
            colour=colours[party.colour],
        )
        file_embed = discord.File(party.image_path, filename="party.png")
        partyEmbed.set_author(name=self.name, icon_url=self.avatar_url)
        partyEmbed.set_image(url="attachment://party.png")
        await president.send(file_embed, partyEmbed)

    async def send(self, fileObj, embedObj):
        await self.__user.send(file=fileObj, embed=embedObj)
