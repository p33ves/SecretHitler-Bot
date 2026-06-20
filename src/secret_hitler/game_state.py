from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from discord.ext.commands import Context
    from .board_powers import Power
    from .game_handler import Game


class GamePhase(Enum):
    """Identifies the current phase of the game."""
    Inactive = 0
    Nomination = 1
    Election = 2
    Legislation = 3
    Execution = 4
    GameOver = None

    def is_active(self) -> bool:
        """Returns True when the game is in active play (past joining, not over)."""
        return self.value is not None and self.value > 0


class GameState(ABC):
    """
    Abstract base for all game states.

    Each concrete subclass owns the behaviour for one phase of the game and
    is responsible for validating commands and triggering state transitions via
    the Game context. Default implementations reject commands that are not
    valid in the current phase.
    """

    @property
    @abstractmethod
    def phase(self) -> GamePhase: ...

    async def on_pick(self, ctx: Context, arg: str, game: Game) -> None:
        await ctx.send(f"Sorry {ctx.author.name}, that's an invalid command at the moment")

    async def on_vote(self, ctx: Context, arg: str, game: Game) -> None:
        await ctx.send(f"Sorry {ctx.author.name}, that's an invalid command at the moment")

    async def on_see(self, ctx: Context, game: Game) -> None:
        await ctx.send(f"Sorry {ctx.author.name}, this seems to be an invalid command")

    async def on_veto(self, ctx: Context, game: Game) -> None:
        await game.channel.send(
            f"Sorry {ctx.author.name}, you don't have the power to veto right now!"
        )


class InactiveState(GameState):
    """Board is open and accepting joins; game play has not yet started."""

    @property
    def phase(self) -> GamePhase:
        return GamePhase.Inactive


class NominationState(GameState):
    """President nominates a chancellor candidate."""

    @property
    def phase(self) -> GamePhase:
        return GamePhase.Nomination

    async def on_pick(self, ctx: Context, arg: str, game: Game) -> None:
        if await game.players.pickChancellor(ctx, arg):
            game.board.clearEdit()
            game.transition(ElectionState())
            await game.board.showBoard(
                game.channel, game.state, game.players, game.current_power
            )


class ElectionState(GameState):
    """All players vote on the nominated president/chancellor pair."""

    @property
    def phase(self) -> GamePhase:
        return GamePhase.Election

    async def on_vote(self, ctx: Context, arg: str, game: Game) -> None:
        if await game.players.markVote(ctx, arg):
            await game.board.showBoard(
                game.channel, game.state, game.players, game.current_power
            )
            if game.players.votingComplete():
                await game.resolve_election()


class LegislationState(GameState):
    """President discards one policy; chancellor enacts one."""

    @property
    def phase(self) -> GamePhase:
        return GamePhase.Legislation

    async def on_pick(self, ctx: Context, arg: str, game: Game) -> None:
        from .board_powers import Power
        flag = await game.board.pickPolicy(game.channel, ctx, arg, game.players)
        if flag is True:
            # President discarded — if killVeto was pending it is now forfeited
            if game.current_power == Power.killVeto:
                game.clear_power()
            return
        if flag is False:
            return
        # Chancellor enacted a policy; flag is Power | None
        game.board.clearEdit()
        fascist_count, liberal_count = game.board.getCardCount()
        if await game.check_win(fascist_count, liberal_count):
            game.transition(GameOverState())
            return
        if fascist_count > 3:
            game.enable_danger_zone()
        if flag:
            game.set_power(flag)
            game.transition(ExecutionState())
        else:
            game.players.nextPresident()
            game.transition(NominationState())
        await game.board.showBoard(
            game.channel, game.state, game.players, game.current_power
        )

    async def on_veto(self, ctx: Context, game: Game) -> None:
        from .board_powers import Power
        if (
            game.current_power != Power.killVeto
            or game.players.president.id != ctx.author.id
        ):
            await game.channel.send(
                f"Sorry {ctx.author.name}, you don't have the power to veto right now!"
            )
            return
        game.clear_power()
        game.board.clearEdit()
        game.players.nextPresident()
        game.transition(NominationState())
        await game.board.showBoard(
            game.channel, game.state, game.players, game.current_power
        )


class ExecutionState(GameState):
    """President exercises a presidential power."""

    @property
    def phase(self) -> GamePhase:
        return GamePhase.Execution

    async def on_pick(self, ctx: Context, arg: str, game: Game) -> None:
        from .board_powers import Power
        from .players_manager import Players
        if ctx.author.id != game.players.president.id:
            await ctx.send(
                f"Sorry {ctx.author.name}, only the President can execute Presidential Powers"
            )
            return
        candidate_id = Players.parse_mention(arg)
        if (
            candidate_id is None
            or not game.players.checkPlayerID(candidate_id)
            or candidate_id == game.players.president.id
        ):
            await ctx.send(
                f"Sorry {ctx.author.name}, that's an invalid selection, please retry!"
            )
            return

        power = game.current_power
        if power in (Power.kill, Power.killVeto):
            await game.players.assassinate(game.channel, candidate_id)
            game.players.nextPresident()
        elif power == Power.getParty:
            await game.players.inspect(game.channel, candidate_id)
            game.players.nextPresident()
        elif power == Power.nextPresident:
            await game.players.chooseSuccessor(game.channel, candidate_id)
        else:
            raise ValueError(f"Unknown power: {power}")

        game.board.clearEdit()
        game.transition(NominationState())
        if power != Power.killVeto:
            game.clear_power()
        await game.board.showBoard(
            game.channel, game.state, game.players, game.current_power
        )

    async def on_see(self, ctx: Context, game: Game) -> None:
        from .board_powers import Power
        if (
            game.current_power != Power.peekTop3
            or game.players.president.id != ctx.author.id
        ):
            await ctx.send(
                f"Sorry {ctx.author.name}, this seems to be an invalid command"
            )
            return
        await game.board.executeTop3(game.players.president)
        game.clear_power()
        game.board.clearEdit()
        game.players.nextPresident()
        game.transition(NominationState())
        await game.channel.send(
            f"President {ctx.author.name} has peeked the next set of Policies"
        )
        await game.board.showBoard(
            game.channel, game.state, game.players, game.current_power
        )


class GameOverState(GameState):
    """The game has concluded."""

    @property
    def phase(self) -> GamePhase:
        return GamePhase.GameOver
