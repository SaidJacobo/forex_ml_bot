from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from app.view_models.bot_trade_performance_vm import BotTradePerformamceVM



class MontecarloVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    model_config = ConfigDict(from_attributes=True)

    Id: UUID
    BotPerformanceId: UUID
    Method: str
    Metric: str
    ColumnName: str
    Value: float