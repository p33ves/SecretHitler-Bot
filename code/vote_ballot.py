from enum import Enum
from typing import Optional


class Vote(Enum):
    NEIN = 0
    JA = 1


class BallotBox:
    def __init__(self):
        self.__voted_ja: set = set()
        self.__voted_nein: set = set()

    def vote(self, player_id, vote: Vote) -> None:
        if player_id in self.__voted_ja or player_id in self.__voted_nein:
            return
        if vote == Vote.JA:
            self.__voted_ja.add(player_id)
        elif vote == Vote.NEIN:
            self.__voted_nein.add(player_id)

    def getTotalVoteCount(self) -> int:
        return len(self.__voted_ja) + len(self.__voted_nein)

    def getVoteSplit(self) -> tuple:
        return len(self.__voted_ja), len(self.__voted_nein)

    def result(self) -> Vote:
        return Vote.JA if len(self.__voted_ja) > len(self.__voted_nein) else Vote.NEIN

    def getVote(self, player_id) -> Optional[Vote]:
        if player_id in self.__voted_ja:
            return Vote.JA
        if player_id in self.__voted_nein:
            return Vote.NEIN
        return None
