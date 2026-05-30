from typing import Optional

import discord
from discord.ext.commands import Context
from PIL import Image

from vote_ballot import Vote
from board_powers import BoardType, Power
from game_state import GameState, GamePhase
from role_player import Player
from players_manager import Players
from policy_pile import Policy, PolicyPile
from static_data import colours, coordinates, images


class Board:
    def __init__(self):
        self.__messageToEdit = None
        self.__type: Optional[BoardType] = None
        self.__base: str = ""
        self.__policyPile = PolicyPile()
        self.__failedElection: int = 0
        self.__fascistPolicies: int = 0
        self.__liberalPolicies: int = 0

    def __getImage(self, channel_id: int) -> str:
        baseImg = Image.open(self.__base)
        dot = Image.open(images["dot.png"])
        new = baseImg.copy()
        new.paste(dot, coordinates["failedElection"][self.__failedElection], dot)
        path = images["currentboard.png"].replace("<channelID>", str(channel_id))
        new.save(path, "PNG")
        return path

    def __placePolicy(self, card: Policy, channel_id: int) -> Optional[Power]:
        baseImg = Image.open(self.__base)
        new = baseImg.copy()
        power = None
        if card == Policy.Fascist:
            cardImg = Image.open(card.getImageUrl())
            new.paste(cardImg, coordinates[card.name][self.__fascistPolicies])
            self.__fascistPolicies += 1
            power = self.__type.getPowers(self.__fascistPolicies)
        elif card == Policy.Liberal:
            cardImg = Image.open(card.getImageUrl())
            new.paste(cardImg, coordinates[card.name][self.__liberalPolicies])
            self.__liberalPolicies += 1
        path = images["newbase.png"].replace("<channelID>", str(channel_id))
        new.save(path, "PNG")
        self.__base = path
        return power

    @property
    def policyPile(self) -> PolicyPile:
        return self.__policyPile

    def setType(self, numOfPlayers: int) -> None:
        if numOfPlayers < 7:
            self.__type = BoardType.FiveToSix
        elif numOfPlayers < 9:
            self.__type = BoardType.SevenToEight
        else:
            self.__type = BoardType.NineToTen
        self.__base = self.__type.getBaseBoard()

    def clearEdit(self) -> None:
        self.__messageToEdit = None

    def getCardCount(self) -> tuple:
        return self.__fascistPolicies, self.__liberalPolicies

    async def openBoard(self, channel, user) -> None:
        playersEmbed = discord.Embed(
            title="**\t Player List **",
            description="A board has been opened. Please enter *sh!join* if you wish to join the game.",
            colour=colours["AQUA"],
        )
        file_embed = discord.File(images["banner.jpg"], filename="banner.jpg")
        playersEmbed.set_author(name=user.name, icon_url=user.display_avatar.url)
        playersEmbed.set_image(url="attachment://banner.jpg")
        playersEmbed.set_footer(text="Player limit: 5-10")
        self.__messageToEdit = await channel.send(file=file_embed, embed=playersEmbed)

    async def joinBoard(self, channel, userName: str, playerCount: int) -> None:
        newEmbed = self.__messageToEdit.embeds[0].copy()
        newEmbed.set_image(url="attachment://banner.jpg")
        newEmbed.add_field(name=playerCount, value=userName)
        newEmbed.set_footer(text=f"{playerCount}/10 players joined")
        await self.__messageToEdit.edit(embed=newEmbed)

    async def beginBoard(self, channel) -> bool:
        self.clearEdit()
        await channel.send(
            "*The year is 1932. The place is pre-WWII Germany. "
            "In Secret Hitler, players are German politicians attempting to hold a fragile Liberal government together and stem the rising tide of Fascism. "
            "Watch out though— there are secret Fascists among you, and one of them is the Secret Hitler. "
            "There are a total of 17 policies (11 Fascist and 6 Liberal) to choose from. "
            "Your roles will be sent to you as a Private Message. The future of the world depends on you. "
            "So play wisely and remember, trust* ***no one.***"
        )
        return True

    async def showBoard(
        self,
        channel,
        state: GameState,
        players: Players,
        power: Optional[Power],
    ) -> None:
        phase = state.phase

        if phase == GamePhase.Nomination:
            desc = f"<@!{players.president.id}>, please pick the chancellor by typing *sh!p @<candidate name>*"
            col = "PURPLE"
        elif phase == GamePhase.Election:
            desc = "All players, please enter *sh!v ja* → vote **YES** or *sh!v nein* → vote **NO**"
            col = "GREEN"
        elif phase == GamePhase.Legislation:
            desc = "The President and Chancellor are enacting policies via private message"
            col = "LIGHT_GREY"
        elif phase == GamePhase.Execution:
            col = "DARK_VIVID_PINK"
            if power is None:
                raise ValueError("Execution state requires a current power")
            if power == Power.getParty:
                desc = f"<@!{players.president.id}>, inspect a player's party by typing *sh!p @<candidate name>*"
            elif power == Power.nextPresident:
                desc = f"<@!{players.president.id}>, choose the next President by typing *sh!p @<candidate name>*"
            elif power == Power.peekTop3:
                desc = f"<@!{players.president.id}>, peek the next 3 policies by typing *sh!see*"
            elif power == Power.kill:
                desc = f"<@!{players.president.id}>, assassinate a player by typing *sh!p @<candidate name>*"
            elif power == Power.killVeto:
                desc = (
                    f"<@!{players.president.id}>, assassinate a player by typing *sh!p @<candidate name>* "
                    "or veto the drawn policies with *sh!veto*"
                )
            else:
                raise ValueError(f"Unknown power: {power}")
        else:
            return

        tableEmbed = discord.Embed(
            title=f"***\t {phase.name}*** Stage",
            description=desc,
            colour=colours[col],
        )
        file_embed = discord.File(self.__getImage(channel.id), filename="board.png")
        tableEmbed.set_author(
            name=players.president.name, icon_url=players.president.avatar_url
        )
        tableEmbed.set_footer(
            text=f"Cards remaining in draw pile: {self.__policyPile.noOfCardsInDeck}"
        )
        for player in players.getPlayers():
            if player.isDead:
                tableEmbed.add_field(name=f"~~{player.name}~~", value="Dead")
                continue
            if phase == GamePhase.Nomination:
                if player.id == players.president.id:
                    val = "Current President"
                elif player.id == players.prevChancellorID:
                    val = "Previous Chancellor"
                elif player.id == players.prevPresidentID:
                    val = "Previous President"
                else:
                    val = "Waiting for chancellor nomination"
            elif phase == GamePhase.Election:
                player_vote = players.ballotBox.getVote(player.id)
                val = "Yet to vote" if player_vote is None else f"Voted {player_vote.name}"
            elif phase == GamePhase.Legislation:
                if player.id in (players.president.id, players.chancellor.id):
                    val = "Picking policy"
                else:
                    val = "Waiting for policy legislation"
            elif phase == GamePhase.Execution:
                val = "Enacting power" if player.id == players.president.id else "Waiting for power execution"
            else:
                val = ""
            tableEmbed.add_field(name=player.name, value=val)

        tableEmbed.set_image(url=f"attachment://{file_embed.filename}")
        if self.__messageToEdit is None:
            self.__messageToEdit = await channel.send(file=file_embed, embed=tableEmbed)
        else:
            await self.__messageToEdit.edit(embed=tableEmbed)

    async def electionResult(self, channel, players: Players) -> Optional[bool]:
        """
        Processes a completed vote and returns:
          None  — election passed (move to legislation)
          False — election failed, failure counter incremented but < 3
          True  — election failed and counter hit 3 (random policy must be placed)
        """
        result = players.ballotBox.result()
        jaCount, neinCount = players.ballotBox.getVoteSplit()
        players.clearBallot()

        if result == Vote.NEIN:
            self.__failedElection += 1
            if self.__failedElection == 3:
                desc = "The top policy will be drawn and placed"
                flag: Optional[bool] = True
            else:
                desc = "Failed election marker moves forward"
                flag = False
            col = "DARK_RED"
            img = images["vote.png"]["Nein"]
            resultTitle = "\t Election *Failed*"
        else:
            self.__failedElection = 0
            flag = None
            col = "DARK_GOLD"
            img = images["vote.png"]["Ja"]
            resultTitle = "\t Election *Passed*"
            desc = "Democracy prevails"

        result_embed = discord.Embed(
            title=resultTitle, description=desc, colour=colours[col]
        )
        file_embed = discord.File(img, filename="vote.png")
        result_embed.set_image(url="attachment://vote.png")
        result_embed.set_footer(text=f"with splits of {jaCount} - {neinCount}")
        await channel.send(file=file_embed, embed=result_embed)
        return flag

    async def placeRandomPolicy(self, channel) -> tuple:
        top = self.__policyPile.placeTopPolicy()
        self.__failedElection = 0
        self.__placePolicy(top, channel.id)
        await channel.send(
            f"A {top.name} policy has been drawn from the pile and placed automatically"
        )
        return self.getCardCount()

    async def pickPolicy(
        self,
        channel,
        ctx: Context,
        arg: str,
        players: Players,
    ) -> "bool | Power | None":
        """
        Handles a policy selection command.
        Returns:
          True            — president discarded a card (chancellor's turn pending)
          False           — invalid action, error sent to user
          Power | None    — chancellor enacted a policy; value is triggered power or None
        """
        if ctx.author.id not in (players.president.id, players.chancellor.id):
            await ctx.send(
                f"Sorry {ctx.author.name}, that's an invalid selection. "
                "Please wait for the President and Chancellor to pick"
            )
            return False
        chosen = Policy.getEnum(arg)
        if chosen is None:
            await ctx.send(
                f"Sorry {ctx.author.name}, that's an invalid selection. Please retry!"
            )
            return False

        cards_in_play = self.__policyPile.cardsInPlay
        if ctx.author.id == players.president.id and len(cards_in_play) == 3:
            await ctx.send(
                f"You discarded {chosen.name}. Sending the rest to {players.chancellor.name} now."
            )
            await self.policyPile.chancellorTurn(players.chancellor, chosen)
            return True
        if ctx.author.id == players.chancellor.id and len(cards_in_play) == 2:
            await ctx.send(f"You picked {chosen.name}. Enacting it on the board now.")
            self.__policyPile.acceptPolicy(chosen)
            await channel.send(f"A ***{chosen.name}*** policy has been placed on the board")
            return self.__placePolicy(chosen, channel.id)

        await ctx.send(
            f"Sorry {ctx.author.name}, that's an invalid selection at the moment"
        )
        return False
