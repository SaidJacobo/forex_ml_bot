from enum import Enum


class ClosePositionType(Enum):
    TAKE_PROFIT = 0
    STOP_LOSS = 1
    TIME = 2

class OperationType(Enum):
    BUY = 0
    SELL = 1

class ActionType(Enum):
    OPEN = 0
    CLOSE = 1
    WAIT = 2
    UPDATE = 3
    CLOSE_ALL = 4