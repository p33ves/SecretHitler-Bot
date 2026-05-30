import pytest
from vote_ballot import BallotBox, Vote


class TestBallotBox:
    def test_ja_vote_recorded(self):
        box = BallotBox()
        box.vote(1, Vote.JA)
        assert box.getVote(1) == Vote.JA

    def test_nein_vote_recorded(self):
        box = BallotBox()
        box.vote(1, Vote.NEIN)
        assert box.getVote(1) == Vote.NEIN

    def test_vote_is_idempotent(self):
        box = BallotBox()
        box.vote(1, Vote.JA)
        box.vote(1, Vote.NEIN)  # second vote must be ignored
        assert box.getVote(1) == Vote.JA

    def test_unvoted_player_returns_none(self):
        box = BallotBox()
        assert box.getVote(999) is None

    def test_empty_box_total_is_zero(self):
        box = BallotBox()
        assert box.getTotalVoteCount() == 0

    def test_total_count(self):
        box = BallotBox()
        box.vote(1, Vote.JA)
        box.vote(2, Vote.NEIN)
        box.vote(3, Vote.JA)
        assert box.getTotalVoteCount() == 3

    def test_vote_split(self):
        box = BallotBox()
        box.vote(1, Vote.JA)
        box.vote(2, Vote.JA)
        box.vote(3, Vote.NEIN)
        assert box.getVoteSplit() == (2, 1)

    def test_result_ja_majority(self):
        box = BallotBox()
        box.vote(1, Vote.JA)
        box.vote(2, Vote.JA)
        box.vote(3, Vote.NEIN)
        assert box.result() == Vote.JA

    def test_result_nein_majority(self):
        box = BallotBox()
        box.vote(1, Vote.NEIN)
        box.vote(2, Vote.NEIN)
        box.vote(3, Vote.JA)
        assert box.result() == Vote.NEIN

    def test_result_tie_goes_to_nein(self):
        box = BallotBox()
        box.vote(1, Vote.JA)
        box.vote(2, Vote.NEIN)
        assert box.result() == Vote.NEIN

    def test_multiple_distinct_players(self):
        box = BallotBox()
        for i in range(10):
            box.vote(i, Vote.JA if i % 2 == 0 else Vote.NEIN)
        assert box.getTotalVoteCount() == 10
        assert box.getVoteSplit() == (5, 5)
