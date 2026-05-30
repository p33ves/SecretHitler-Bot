from __future__ import annotations

from typing import Optional

import discord
from discord.ext.commands import Context

from game_state import (
    GameState, GamePhase,
    InactiveState, NominationState, LegislationState, GameOverState,
)
from game_board import Board
from players_manager import Players
from board_powers import Power


class Game:
    """
    Owns the game context and coordinates between state classes, the board,
    and the player roster. Command methods delegate entirely to the current
    GameState, which calls back through the public interface defined here.
    """

    def __init__(self, channel: discord.TextChannel, user: discord.User):
        self.channel = channel
        self._owner = user
        self._state: GameState = InactiveState()
        self._board = Board()
        self._players = Players()
        self._current_power: Optional[Power] = None
        self._danger_zone = False

    # ------------------------------------------------------------------ #
    # Read-only interface consumed by GameState subclasses                 #
    # ------------------------------------------------------------------ #

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def players(self) -> Players:
        return self._players

    @property
    def board(self) -> Board:
        return self._board

    @property
    def current_power(self) -> Optional[Power]:
        return self._current_power

    # ------------------------------------------------------------------ #
    # Mutation interface consumed by GameState subclasses                  #
    # ------------------------------------------------------------------ #

    def transition(self, new_state: GameState) -> None:
        self._state = new_state

    def set_power(self, power: Power) -> None:
        self._current_power = power

    def clear_power(self) -> None:
        self._current_power = None

    def enable_danger_zone(self) -> None:
        self._danger_zone = True

    # ------------------------------------------------------------------ #
    # Lifecycle commands (called by Engine)                                #
    # ------------------------------------------------------------------ #

    async def launch(self) -> None:
        await self._board.openBoard(self.channel, self._owner)

    async def join(self, user: discord.User) -> bool:
        if self._state.phase != GamePhase.Inactive:
            await self.channel.send(
                f"Sorry {user.name}, that's an invalid command at the moment"
            )
            return False
        if await self._players.addPlayer(self.channel, user):
            await self._board.joinBoard(self.channel, user.name, self._players.count)
            return True
        return False

    async def begin(self, user: discord.User) -> None:
        if user.id != self._owner.id:
            await self.channel.send(
                f"Sorry {user.name}, only the game owner can begin the game"
            )
            return
        if (
            await self._players.beginGame(self.channel, user)
            and await self._board.beginBoard(self.channel)
        ):
            await self._players.generateRoles()
            self._board.setType(self._players.count)
            self.transition(NominationState())
            await self._board.showBoard(
                self.channel, self._state, self._players, self._current_power
            )

    # ------------------------------------------------------------------ #
    # In-game commands — fully delegated to the current state              #
    # ------------------------------------------------------------------ #

    async def pick(self, ctx: Context, arg: str) -> None:
        await self._state.on_pick(ctx, arg, self)

    async def vote(self, ctx: Context, arg: str) -> None:
        await self._state.on_vote(ctx, arg, self)

    async def see(self, ctx: Context) -> None:
        await self._state.on_see(ctx, self)

    async def veto(self, ctx: Context) -> None:
        await self._state.on_veto(ctx, self)

    # ------------------------------------------------------------------ #
    # Shared async operations called back from state classes               #
    # ------------------------------------------------------------------ #

    async def resolve_election(self) -> None:
        """Process a completed election vote and advance the game state."""
        self._board.clearEdit()
        flag = await self._board.electionResult(self.channel, self._players)
        if flag is None:
            # Election passed — move to legislation
            self._players.freezePrevious()
            if self._danger_zone and await self.check_win():
                self.transition(GameOverState())
                return
            self.transition(LegislationState())
            await self._board.showBoard(
                self.channel, self._state, self._players, self._current_power
            )
            await self._board.policyPile.presidentTurn(
                self.channel, self._players.president
            )
        else:
            if flag:
                # Three consecutive failed elections — place top policy automatically
                fascist_count, liberal_count = await self._board.placeRandomPolicy(
                    self.channel
                )
                if await self.check_win(fascist_count, liberal_count):
                    self.transition(GameOverState())
                    return
                if fascist_count > 3:
                    self.enable_danger_zone()
            self.transition(NominationState())
            self._players.nextPresident()
            await self._board.showBoard(
                self.channel, self._state, self._players, self._current_power
            )

    async def check_win(self, fascist_count: int = 0, liberal_count: int = 0) -> bool:
        """Evaluate all win conditions. Returns True if the game is over."""
        if (
            not (fascist_count or liberal_count)
            and self._danger_zone
            and self._players.chancellor is not None
            and self._players.hitler.id == self._players.chancellor.id
        ):
            await self.channel.send("Fascists win! Hitler has been made Chancellor")
            return True
        if fascist_count == 6:
            await self.channel.send("Fascists win! 6 Fascist policies have been passed")
            return True
        if liberal_count == 5:
            await self.channel.send("Liberals win! 5 Liberal policies have been passed")
            return True
        for player in self._players.getPlayers():
            if player.id == self._players.hitler.id and player.isDead:
                await self.channel.send("Liberals win! Hitler has been assassinated")
                return True
        return False
