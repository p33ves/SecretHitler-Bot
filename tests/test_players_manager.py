import pytest
from unittest.mock import MagicMock, AsyncMock

from players_manager import Players, HitlerInfo
from vote_ballot import Vote


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_player(uid: int, name: str = "player", dead: bool = False):
    p = MagicMock()
    p.id = uid
    p.name = name
    p.isDead = dead
    p.setRole = MagicMock()
    p.sendRole = AsyncMock()
    return p


def _make_players(count: int, dead_indices: list = None) -> Players:
    """Return a Players instance pre-populated with `count` mock players."""
    dead_indices = dead_indices or []
    players = Players()
    for i in range(count):
        players._Players__playerList.append(
            _make_mock_player(i, f"player{i}", dead=(i in dead_indices))
        )
    return players


def _make_channel():
    ch = MagicMock()
    ch.send = AsyncMock()
    return ch


# ---------------------------------------------------------------------------
# HitlerInfo dataclass
# ---------------------------------------------------------------------------

class TestHitlerInfo:
    def test_fields_accessible(self):
        info = HitlerInfo(id=42, name="SecretHitler")
        assert info.id == 42
        assert info.name == "SecretHitler"

    def test_frozen_prevents_mutation(self):
        info = HitlerInfo(id=1, name="H")
        with pytest.raises(AttributeError):
            info.id = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# nextPresident
# ---------------------------------------------------------------------------

class TestNextPresident:
    def test_advances_to_next_alive_player(self):
        players = _make_players(5)
        players.nextPresident()
        assert players.president.id == 1

    def test_wraps_around_end_of_list(self):
        players = _make_players(3)
        players._Players__presidentElectIndex = 2
        players.nextPresident()
        assert players.president.id == 0

    def test_skips_single_dead_player(self):
        players = _make_players(4, dead_indices=[1])
        players.nextPresident()
        assert players.president.id == 2

    def test_skips_multiple_consecutive_dead_players(self):
        players = _make_players(5, dead_indices=[1, 2, 3])
        players.nextPresident()
        assert players.president.id == 4

    def test_skips_dead_player_wrapping_around(self):
        players = _make_players(4, dead_indices=[0])
        players._Players__presidentElectIndex = 3
        players.nextPresident()
        assert players.president.id == 1

    def test_raises_when_all_players_dead(self):
        players = _make_players(3, dead_indices=[0, 1, 2])
        with pytest.raises(ValueError, match="All players are dead"):
            players.nextPresident()

    def test_choose_by_explicit_index(self):
        players = _make_players(5)
        players.nextPresident(newIndex=4)
        assert players.president.id == 4

    def test_explicit_index_out_of_bounds_raises(self):
        players = _make_players(3)
        with pytest.raises(ValueError):
            players.nextPresident(newIndex=10)

    def test_clears_chancellor_after_advance(self):
        players = _make_players(3)
        players._Players__chancellorElectID = 99
        players.nextPresident()
        assert players.chancellor is None


# ---------------------------------------------------------------------------
# Chancellor property
# ---------------------------------------------------------------------------

class TestChancellor:
    def test_chancellor_none_when_not_set(self):
        players = _make_players(3)
        assert players.chancellor is None

    def test_chancellor_returns_correct_player(self):
        players = _make_players(3)
        players._Players__chancellorElectID = 2
        assert players.chancellor.id == 2

    def test_chancellor_none_for_unknown_id(self):
        players = _make_players(3)
        players._Players__chancellorElectID = 999
        assert players.chancellor is None


# ---------------------------------------------------------------------------
# checkPlayerID
# ---------------------------------------------------------------------------

class TestCheckPlayerID:
    def test_alive_player_found(self):
        players = _make_players(5)
        assert players.checkPlayerID(3) is True

    def test_dead_player_not_found(self):
        players = _make_players(5, dead_indices=[3])
        assert players.checkPlayerID(3) is False

    def test_unknown_id_not_found(self):
        players = _make_players(5)
        assert players.checkPlayerID(999) is False


# ---------------------------------------------------------------------------
# playersAlive
# ---------------------------------------------------------------------------

class TestPlayersAlive:
    def test_all_alive(self):
        players = _make_players(5)
        assert len(players.playersAlive) == 5

    def test_excludes_dead(self):
        players = _make_players(5, dead_indices=[1, 3])
        assert len(players.playersAlive) == 3

    def test_all_dead_returns_empty(self):
        players = _make_players(3, dead_indices=[0, 1, 2])
        assert players.playersAlive == []


# ---------------------------------------------------------------------------
# Voting helpers
# ---------------------------------------------------------------------------

class TestVotingHelpers:
    def test_voting_incomplete_when_not_all_voted(self):
        players = _make_players(5)
        players.ballotBox.vote(0, Vote.JA)
        assert players.votingComplete() is False

    def test_voting_complete_when_all_alive_voted(self):
        players = _make_players(5)
        for i in range(5):
            players.ballotBox.vote(i, Vote.JA)
        assert players.votingComplete() is True

    def test_dead_players_excluded_from_vote_count(self):
        players = _make_players(5, dead_indices=[4])
        for i in range(4):  # only 4 alive
            players.ballotBox.vote(i, Vote.JA)
        assert players.votingComplete() is True

    def test_clear_ballot_resets_votes(self):
        players = _make_players(3)
        players.ballotBox.vote(0, Vote.JA)
        players.clearBallot()
        assert players.ballotBox.getTotalVoteCount() == 0

    def test_freeze_previous_records_president_and_chancellor(self):
        players = _make_players(3)
        players._Players__chancellorElectID = 2
        players.freezePrevious()
        assert players.prevPresidentID == 0
        assert players.prevChancellorID == 2
