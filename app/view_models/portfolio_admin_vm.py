from typing import List, TYPE_CHECKING, Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import date

from app.view_models.bot_performance_metrics_vm import PerformanceMetricsVM

class PortfolioAdminVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    FavoritesAndRobusts: List[PerformanceMetricsVM]
    Selected: List[PerformanceMetricsVM] = None