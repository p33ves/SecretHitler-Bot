from __future__ import annotations

import random
from enum import Enum
from typing import TYPE_CHECKING, Optional

import discord

from .static_data import colours, images

if TYPE_CHECKING:
    from .players_manager import HitlerInfo


class Role(Enum):
    Hitler = 1
    Fascist = 2
    Liberal = 3

    def getRolePic(self) -> str:
        if self == Role.Hitler:
            return images["role.png"]["Hitler"]
        if self == Role.Fascist:
            return random.choice(images["role.png"]["Fascist"])
        return random.choice(images["role.png"]["Liberal"])


class Player:
    def __init__(self, user):
        self.__user = user
        self.__role = None
        self.__isDead = False
        self.__channel = None

    def set_channel(self, channel) -> None:
        self.__channel = channel

    @property
    def id(self) -> str:
        return self.__user.id

    @property
    def name(self) -> str:
        # TODO If same player names join the same game, need to change this into full_name
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

    async def sendRole(self, count: int, fascists: dict, hitler: Optional[HitlerInfo]) -> None:
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
        file_embed = discord.File(self.__role.getRolePic(), filename="role.png")
        roleEmbed.set_author(name=self.name, icon_url=self.avatar_url)
        roleEmbed.set_image(url="attachment://role.png")
        await self.send(file_embed, roleEmbed)

    async def revealParty(self, president) -> None:
        if self.__role == Role.Liberal:
            party_name, img_key, col = "Liberal", "Liberal", "DARK_BLUE"
        else:
            party_name, img_key, col = "Fascist", "Fascist", "RED"
        partyEmbed = discord.Embed(
            title=f"{self.name} is from ***{party_name}*** party",
            colour=colours[col],
        )
        file_embed = discord.File(images["party.png"][img_key], filename="party.png")
        partyEmbed.set_author(name=self.name, icon_url=self.avatar_url)
        partyEmbed.set_image(url="attachment://party.png")
        await president.send(file_embed, partyEmbed)

    async def send(self, fileObj, embedObj):
        try:
            await self.__user.send(file=fileObj, embed=embedObj)
        except discord.Forbidden:
            if self.__channel:
                await self.__channel.send(
                    f"⚠️ Could not send a DM to **{self.name}**. "
                    "Please enable DMs from server members to participate."
                )
