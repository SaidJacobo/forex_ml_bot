from typing import Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import date

class TradeVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Id: UUID
    BotPerformanceId: UUID
    Size: int
    EntryBar: int
    ExitBar: int
    EntryPrice: float
    ExitPrice: float
    PnL: float
    ReturnPct: float
    EntryTime: date
    ExitTime: date
    Duration: int
    Equity: float
    TopBest: Optional[bool] = None
    TopWorst: Optional[bool] = None