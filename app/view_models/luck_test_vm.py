from typing import List, TYPE_CHECKING, Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import date

from app.view_models.bot_performance_metrics_vm import PerformanceMetricsVM

class LuckTestVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    Id: UUID
    BotPerformanceId: UUID
    LuckTestPerformanceId: UUID
    TradesPercentToRemove: float
    
    LuckTestPerformance: PerformanceMetricsVM

