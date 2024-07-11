from enum import Enum


class ClosePositionType(Enum):
    TAKE_PROFIT = 0
    STOP_LOSS = 1
    DAYS = 2
    TAKE_PROFIT_RANDOM = 3
    STOP_LOSS_RANDOM = 4

class OperationType(Enum):
    BUY = 0
    SELL = 1

class ActionType(Enum):
    OPEN = 0
    CLOSE = 1
    WAIT = 2
    UPDATE = 3