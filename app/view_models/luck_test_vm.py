from typing import List, TYPE_CHECKING, Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import date


class LuckTestPerformanceVM(BaseModel):
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

class LuckTestVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    Id: UUID
    BotPerformanceId: UUID
    LuckTestPerformanceId: UUID
    TradesPercentToRemove: float
    
    LuckTestPerformance: LuckTestPerformanceVM

