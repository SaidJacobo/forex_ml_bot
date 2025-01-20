from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from app.view_models.bot_trade_performance_vm import BotTradePerformamceVM
from app.view_models.bot_vm import BotVM
from datetime import date
from app.view_models.montecarlo_vm import MontecarloVM
from app.view_models.trade_vm import TradeVM


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
    TradeHistory: List[TradeVM]
    MontecarloTest: Optional[MontecarloVM] = None
    InitialCash: float