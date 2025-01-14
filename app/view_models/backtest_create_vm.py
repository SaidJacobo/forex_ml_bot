from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from app.view_models.category_vm import CategoryVM
from app.view_models.strategy_vm import StrategyVM
from app.view_models.timeframe_vm import TimeframeVM

class BacktestCreateVM(BaseModel):
    Categories: Optional[List[CategoryVM]] = None
    Strategies: Optional[List[StrategyVM]] = None
    Timeframes: Optional[List[TimeframeVM]] = None
    
    StrategyId: Optional[UUID] = None
    CategoryId: Optional[UUID] = None
    TickerId: Optional[UUID] = None
    TimeframeId: Optional[UUID] = None