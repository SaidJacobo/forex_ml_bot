from typing import Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from app.view_models.bot_trade_performance_vm import BotTradePerformamceVM
from app.view_models.bot_vm import BotVM
from datetime import date


class BotPerformanceVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: UUID
    BotId: UUID
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
    Bot: BotVM
    BotTradePerformance: BotTradePerformamceVM