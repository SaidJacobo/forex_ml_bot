from typing import List, TYPE_CHECKING, Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import date

from app.view_models.bot_trade_performance_vm import BotTradePerformamceVM
from app.view_models.bot_vm import BotVM


class PerformanceMetricsVM(BaseModel):
    Bot: Optional[BotVM] = None
    model_config = ConfigDict(from_attributes=True)
    Id: UUID
    BotId: Optional[UUID]=None
    DateFrom: date
    DateTo: date
    Method: str
    StabilityRatio: float
    Trades: int
    Return: float
    Drawdown: float
    RreturnDd: float
    CustomMetric: float
    WinRate: float
    Duration: int
    Robust: Optional[bool] = None
    InitialCash: float
    BotTradePerformance: Optional[BotTradePerformamceVM] = None
    