import pytest
from unittest.mock import MagicMock, AsyncMock

from secret_hitler.game_state import (
    GamePhase,
    GameState,
    InactiveState,
    NominationState,
    ElectionState,
    LegislationState,
    ExecutionState,
    GameOverState,
)


# ---------------------------------------------------------------------------
# GamePhase.is_active()
# ---------------------------------------------------------------------------

class TestGamePhaseIsActive:
    @pytest.mark.parametrize("phase", [
        GamePhase.Nomination,
        GamePhase.Election,
        GamePhase.Legislation,
        GamePhase.Execution,
    ])
    def test_active_phases(self, phase):
        assert phase.is_active() is True

    @pytest.mark.parametrize("phase", [
        GamePhase.Inactive,
        GamePhase.GameOver,
    ])
    def test_inactive_phases(self, phase):
        assert phase.is_active() is False


# ---------------------------------------------------------------------------
# Concrete state .phase property
# ---------------------------------------------------------------------------

class TestStatePhases:
    @pytest.mark.parametrize("state_cls, expected_phase", [
        (InactiveState,    GamePhase.Inactive),
        (NominationState,  GamePhase.Nomination),
        (ElectionState,    GamePhase.Election),
        (LegislationState, GamePhase.Legislation),
        (ExecutionState,   GamePhase.Execution),
        (GameOverState,    GamePhase.GameOver),
    ])
    def test_phase_property(self, state_cls, expected_phase):
        assert state_cls().phase == expected_phase


# ---------------------------------------------------------------------------
# Default command rejection
# Each state subclass inherits rejections for commands it doesn't override.
# ---------------------------------------------------------------------------

def _make_ctx(author_name="TestUser"):
    ctx = MagicMock()
    ctx.author.name = author_name
    ctx.send = AsyncMock()
    return ctx


def _make_game():
    game = MagicMock()
    game.channel.send = AsyncMock()
    return game


class TestDefaultRejections:
    """States that do not override a command must send an error message."""

    @pytest.mark.asyncio
    async def test_inactive_rejects_pick(self):
        ctx, game = _make_ctx(), _make_game()
        await InactiveState().on_pick(ctx, "arg", game)
        ctx.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_inactive_rejects_vote(self):
        ctx, game = _make_ctx(), _make_game()
        await InactiveState().on_vote(ctx, "ja", game)
        ctx.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_inactive_rejects_see(self):
        ctx, game = _make_ctx(), _make_game()
        await InactiveState().on_see(ctx, game)
        ctx.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_inactive_rejects_veto(self):
        ctx, game = _make_ctx(), _make_game()
        await InactiveState().on_veto(ctx, game)
        game.channel.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_nomination_rejects_vote(self):
        ctx, game = _make_ctx(), _make_game()
        await NominationState().on_vote(ctx, "ja", game)
        ctx.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_nomination_rejects_see(self):
        ctx, game = _make_ctx(), _make_game()
        await NominationState().on_see(ctx, game)
        ctx.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_election_rejects_pick(self):
        ctx, game = _make_ctx(), _make_game()
        await ElectionState().on_pick(ctx, "red", game)
        ctx.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_election_rejects_see(self):
        ctx, game = _make_ctx(), _make_game()
        await ElectionState().on_see(ctx, game)
        ctx.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_legislation_rejects_see(self):
        ctx, game = _make_ctx(), _make_game()
        await LegislationState().on_see(ctx, game)
        ctx.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_game_over_rejects_all_commands(self):
        ctx, game = _make_ctx(), _make_game()
        state = GameOverState()
        await state.on_pick(ctx, "arg", game)
        await state.on_vote(ctx, "ja", game)
        await state.on_see(ctx, game)
        assert ctx.send.await_count == 3
