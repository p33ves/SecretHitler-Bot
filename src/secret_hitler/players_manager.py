import random
from dataclasses import dataclass
from typing import Optional

import discord
from discord.ext.commands import Context

from .vote_ballot import BallotBox, Vote
from .role_player import Role, Player


@dataclass(frozen=True)
class HitlerInfo:
    id: int
    name: str


class Players:
    def __init__(self):
        self.__playerList: list = []
        self.__fascists: dict = {}
        self.__hitler: Optional[HitlerInfo] = None
        self.__presidentElectIndex: int = 0
        self.__chancellorElectID: Optional[int] = None
        self.__prevPresidentID: Optional[int] = None
        self.__prevChancellorID: Optional[int] = None
        self.__ballotBox = BallotBox()

    @property
    def count(self) -> int:
        return len(self.__playerList)

    @property
    def ballotBox(self) -> BallotBox:
        return self.__ballotBox

    @property
    def hitler(self) -> Optional[HitlerInfo]:
        return self.__hitler

    @property
    def prevPresidentID(self) -> Optional[int]:
        return self.__prevPresidentID

    @property
    def prevChancellorID(self) -> Optional[int]:
        return self.__prevChancellorID

    @property
    def playersAlive(self) -> list:
        return [p for p in self.__playerList if not p.isDead]

    @property
    def president(self) -> Player:
        return self.__playerList[self.__presidentElectIndex]

    @property
    def chancellor(self) -> Optional[Player]:
        if self.__chancellorElectID is None:
            return None
        for player in self.__playerList:
            if player.id == self.__chancellorElectID:
                return player
        return None

    def getPlayers(self) -> list:
        return self.__playerList

    def clearBallot(self):
        self.__ballotBox = BallotBox()

    @staticmethod
    def parse_mention(arg: str) -> Optional[int]:
        """Parse a Discord user mention (<@ID> or legacy <@!ID>) to an int ID."""
        if arg.startswith("<@") and arg.endswith(">"):
            uid = arg[2:-1].lstrip("!")
            return int(uid) if uid.isdigit() else None
        return None

    def checkPlayerID(self, id: int) -> bool:
        return any(p.id == id for p in self.playersAlive)

    async def generateRoles(self) -> None:
        rolesList = ["H", "L", "L", "L", "F", "L", "F", "L", "F", "L"]
        reqdRoles = rolesList[: self.count]
        random.shuffle(self.__playerList)
        random.shuffle(reqdRoles)
        for player, role_code in zip(self.__playerList, reqdRoles):
            if role_code == "L":
                player.setRole(Role.Liberal)
            elif role_code == "F":
                player.setRole(Role.Fascist)
                self.__fascists[player.id] = player.name
            else:
                player.setRole(Role.Hitler)
                self.__hitler = HitlerInfo(player.id, player.name)
        for player in self.__playerList:
            await player.sendRole(self.count, self.__fascists, self.__hitler)

    def votingComplete(self) -> bool:
        return len(self.playersAlive) == self.__ballotBox.getTotalVoteCount()

    def freezePrevious(self):
        self.__prevPresidentID = self.president.id
        self.__prevChancellorID = self.chancellor.id

    def nextPresident(self, newIndex: Optional[int] = None) -> None:
        if newIndex is not None:
            if newIndex >= self.count:
                raise ValueError("New president index exceeds player count")
            self.__presidentElectIndex = newIndex
        else:
            candidate = (self.__presidentElectIndex + 1) % self.count
            start = candidate
            while self.__playerList[candidate].isDead:
                candidate = (candidate + 1) % self.count
                if candidate == start:
                    raise ValueError("All players are dead")
            self.__presidentElectIndex = candidate
        self.__chancellorElectID = None

    async def addPlayer(self, channel: discord.TextChannel, user: discord.User) -> bool:
        if self.count > 9:
            await channel.send(
                f"Sorry {user.name}, the current game has reached maximum player limit"
            )
            return False
        p = Player(user)
        p.set_channel(channel)
        self.__playerList.append(p)
        return True

    def removePlayer(self, user_id: int) -> Optional[str]:
        for i, player in enumerate(self.__playerList):
            if player.id == user_id:
                self.__playerList.pop(i)
                return player.name
        return None

    async def beginGame(self, channel: discord.TextChannel, user: discord.User) -> bool:
        if self.count < 5:
            await channel.send(
                f"Sorry {user.name}, the game requires minimum 5 players"
            )
            return False
        return True

    async def pickChancellor(self, ctx: Context, arg: str) -> bool:
        if ctx.author.id != self.president.id:
            await ctx.send(f"Sorry {ctx.author.name}, you are not the president!")
            return False
        candidate_id = Players.parse_mention(arg)
        if (
            candidate_id is None
            or not self.checkPlayerID(candidate_id)
            or candidate_id == self.__prevChancellorID
            or candidate_id == self.president.id
        ):
            await ctx.send(
                f"Sorry {ctx.author.name}, that's an invalid nomination, please retry!"
            )
            return False
        if self.count > 6 and candidate_id == self.__prevPresidentID:
            await ctx.send(
                f"Sorry {ctx.author.name}, that's an invalid nomination, please retry!"
            )
            return False
        self.__chancellorElectID = candidate_id
        return True

    async def markVote(self, ctx: Context, vote: str) -> bool:
        if not self.checkPlayerID(ctx.author.id):
            await ctx.send(f"Sorry {ctx.author.name}, you cannot vote")
        elif vote.upper() not in ("JA", "NEIN"):
            await ctx.send(
                f"Sorry {ctx.author.name}, that's an invalid vote, please retry!"
            )
        else:
            self.__ballotBox.vote(ctx.author.id, Vote[vote.upper()])
            return True
        return False

    async def assassinate(self, channel: discord.TextChannel, playerID: int) -> None:
        for player in self.__playerList:
            if player.id == playerID:
                player.kill()
                await channel.send(
                    f"{player.name} has been assassinated by President {self.president.name}. RIP"
                )
                return

    async def inspect(self, channel: discord.TextChannel, playerID: int) -> None:
        for player in self.__playerList:
            if player.id == playerID:
                await player.revealParty(self.president)
                await channel.send(
                    f"President {self.president.name} has inspected {player.name}'s party membership"
                )
                return

    async def chooseSuccessor(self, channel: discord.TextChannel, playerID: int) -> None:
        for index, player in enumerate(self.__playerList):
            if player.id == playerID:
                self.nextPresident(index)
                return
        raise ValueError(f"Chosen president ID {playerID} not found in player list")
