from enum import Enum
from typing import Optional

from static_data import images


class Power(Enum):
    getParty = 1
    peekTop3 = 2
    nextPresident = 3
    kill = 4
    killVeto = 5


class BoardType(Enum):
    FiveToSix = 1
    SevenToEight = 2
    NineToTen = 3

    def getBaseBoard(self) -> str:
        return images["baseboard.png"][self.name]

    def getPowers(self, cardIndex: int) -> Optional[Power]:
        powers: dict = {4: Power.kill, 5: Power.killVeto}
        if self == BoardType.NineToTen:
            powers[1] = Power.getParty
        if self != BoardType.FiveToSix:
            powers[2] = Power.getParty
            powers[3] = Power.nextPresident
        else:
            powers[3] = Power.peekTop3
        return powers.get(cardIndex)
