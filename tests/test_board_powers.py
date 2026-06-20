import pytest
from secret_hitler.board_powers import BoardType, Power


class TestBoardTypeFiveToSix:
    def test_no_power_at_1(self):
        assert BoardType.FiveToSix.getPowers(1) is None

    def test_no_power_at_2(self):
        assert BoardType.FiveToSix.getPowers(2) is None

    def test_peek_at_3(self):
        assert BoardType.FiveToSix.getPowers(3) == Power.peekTop3

    def test_kill_at_4(self):
        assert BoardType.FiveToSix.getPowers(4) == Power.kill

    def test_kill_veto_at_5(self):
        assert BoardType.FiveToSix.getPowers(5) == Power.killVeto


class TestBoardTypeSevenToEight:
    def test_no_power_at_1(self):
        assert BoardType.SevenToEight.getPowers(1) is None

    def test_get_party_at_2(self):
        assert BoardType.SevenToEight.getPowers(2) == Power.getParty

    def test_next_president_at_3(self):
        assert BoardType.SevenToEight.getPowers(3) == Power.nextPresident

    def test_kill_at_4(self):
        assert BoardType.SevenToEight.getPowers(4) == Power.kill

    def test_kill_veto_at_5(self):
        assert BoardType.SevenToEight.getPowers(5) == Power.killVeto


class TestBoardTypeNineToTen:
    def test_get_party_at_1(self):
        assert BoardType.NineToTen.getPowers(1) == Power.getParty

    def test_get_party_at_2(self):
        assert BoardType.NineToTen.getPowers(2) == Power.getParty

    def test_next_president_at_3(self):
        assert BoardType.NineToTen.getPowers(3) == Power.nextPresident

    def test_kill_at_4(self):
        assert BoardType.NineToTen.getPowers(4) == Power.kill

    def test_kill_veto_at_5(self):
        assert BoardType.NineToTen.getPowers(5) == Power.killVeto


class TestBoardTypeOutOfRange:
    @pytest.mark.parametrize("board_type", list(BoardType))
    def test_no_power_at_0(self, board_type):
        assert board_type.getPowers(0) is None

    @pytest.mark.parametrize("board_type", list(BoardType))
    def test_no_power_beyond_5(self, board_type):
        assert board_type.getPowers(6) is None
        assert board_type.getPowers(99) is None
