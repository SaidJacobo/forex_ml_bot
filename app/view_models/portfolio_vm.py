from typing import List
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.view_models.bot_performance_metrics_vm import PerformanceMetricsVM


class PortfolioVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id:UUID
    Name: str
    Description: str
    Metrics: PerformanceMetricsVM=None
    BotPerformances: List[PerformanceMetricsVM]=None