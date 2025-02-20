from typing import List, TYPE_CHECKING, Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import date

from app.view_models.bot_trade_performance_vm import BotTradePerformamceVM
from app.view_models.bot_vm import BotVM


class PerformanceMetricsVM(BaseModel):
    Bot: Optional[BotVM] = None
    model_config = ConfigDict(from_attributes=True)
    Id: UUID = None
    BotId: Optional[UUID] = None
    DateFrom: date = None
    DateTo: date = None
    Method: str = None
    StabilityRatio: float = None
    Trades: int = None
    Return: float = None
    Drawdown: float = None
    RreturnDd: float = None
    CustomMetric: float = None
    WinRate: float = None
    Duration: int = None
    Favorite: bool = False
    InitialCash: float  = None
    BotTradePerformance: Optional[BotTradePerformamceVM] = None
    