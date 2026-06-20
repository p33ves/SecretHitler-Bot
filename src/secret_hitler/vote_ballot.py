from enum import Enum
from typing import Optional


class Vote(Enum):
    NEIN = 0
    JA = 1


class BallotBox:
    def __init__(self):
        self.__votes: dict = {}

    def vote(self, player_id, vote: Vote) -> None:
        if player_id not in self.__votes:
            self.__votes[player_id] = vote

    def getTotalVoteCount(self) -> int:
        return len(self.__votes)

    def getVoteSplit(self) -> tuple:
        ja = sum(1 for v in self.__votes.values() if v == Vote.JA)
        return ja, len(self.__votes) - ja

    def result(self) -> Vote:
        ja, nein = self.getVoteSplit()
        return Vote.JA if ja > nein else Vote.NEIN

    def getVote(self, player_id) -> Optional[Vote]:
        return self.__votes.get(player_id)
