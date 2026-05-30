import random
from enum import Enum
from typing import List

import discord

from role_player import Player
from static_data import images, colours


class PolicyError(Exception):
    """Raised when a policy operation is attempted in an invalid state."""


class Policy(Enum):
    Fascist = 1
    Liberal = 2

    def getImageUrl(self) -> str:
        return images["policy.png"][self.name]

    @staticmethod
    def getEnum(policy: str) -> "Policy | None":
        policy = policy.lower()
        if policy in ("fascist", "red", "r"):
            return Policy.Fascist
        if policy in ("liberal", "blue", "b"):
            return Policy.Liberal
        return None


class PolicyPile:
    def __init__(self):
        self.__drawPile: List[Policy] = []
        self.__discardPile: List[Policy] = []
        self.__cardsInPlay: List[Policy] = []
        self.__initDrawPile()

    def __initDrawPile(self):
        self.__drawPile = [Policy.Fascist] * 11 + [Policy.Liberal] * 6
        self.__shuffle()

    def __shuffle(self):
        self.__drawPile.extend(self.__discardPile)
        self.__discardPile.clear()
        random.shuffle(self.__drawPile)

    @property
    def noOfCardsInDeck(self) -> int:
        return len(self.__drawPile)

    @property
    def cardsInPlay(self) -> List[Policy]:
        return self.__cardsInPlay

    def draw(self) -> bool:
        if self.__cardsInPlay:
            raise PolicyError("Cannot draw while cards are already in play")
        shuffled = False
        if len(self.__drawPile) < 3:
            self.__shuffle()
            shuffled = True
        self.__cardsInPlay.extend(self.__drawPile[:3])
        self.__drawPile = self.__drawPile[3:]
        return shuffled

    def discardPolicy(self, policy: Policy) -> None:
        if self.__cardsInPlay.count(policy) == 0 or len(self.__cardsInPlay) != 3:
            raise PolicyError("Cannot discard: no matching card or wrong hand size")
        self.__cardsInPlay.remove(policy)
        self.__discardPile.append(policy)

    def acceptPolicy(self, policy: Policy) -> None:
        if self.__cardsInPlay.count(policy) == 0 or len(self.__cardsInPlay) != 2:
            raise PolicyError("Cannot accept: no matching card or wrong hand size")
        self.__cardsInPlay.remove(policy)
        self.__discardPile.extend(self.__cardsInPlay)  # discard remaining card
        self.__cardsInPlay.clear()

    def peekTop3(self) -> List[Policy]:
        return self.__drawPile[:3]

    def placeTopPolicy(self) -> Policy:
        return self.__drawPile.pop(0)

    async def presidentTurn(self, channel, president: Player) -> None:
        shuffled = self.draw()
        if shuffled:
            await channel.send(
                f"The deck has been reshuffled and there are {self.noOfCardsInDeck} cards remaining"
            )
        file_embed = discord.File(
            images["presidentdeck.png"][self.cardsInPlay.count(Policy.Fascist)],
            filename="policydeck.png",
        )
        cardsEmbed = discord.Embed(
            title="\t **Discard** one Policy",
            description="Type *sh!p <color/name>* of the card you wish to discard:",
            colour=colours["DARK_AQUA"],
        )
        cardsEmbed.set_image(url="attachment://policydeck.png")
        await president.send(fileObj=file_embed, embedObj=cardsEmbed)

    async def chancellorTurn(self, chancellor: Player, discarded: Policy) -> None:
        self.discardPolicy(discarded)
        file_embed = discord.File(
            images["chancellordeck.png"][self.cardsInPlay.count(Policy.Fascist)],
            filename="policydeck.png",
        )
        cardsEmbed = discord.Embed(
            title="\t **Pick** one Policy",
            description="Type *sh!p <color/name>* of the card you wish to enact:",
            colour=colours["GOLD"],
        )
        cardsEmbed.set_image(url="attachment://policydeck.png")
        await chancellor.send(fileObj=file_embed, embedObj=cardsEmbed)

    async def executeTop3(self, president: Player) -> None:
        top3 = self.peekTop3()
        file_embed = discord.File(
            images["presidentdeck.png"][top3.count(Policy.Fascist)],
            filename="policydeck.png",
        )
        cardsEmbed = discord.Embed(
            title="\t Next cards in the draw pile",
            colour=colours["DARK_AQUA"],
        )
        cardsEmbed.set_image(url="attachment://policydeck.png")
        await president.send(fileObj=file_embed, embedObj=cardsEmbed)
