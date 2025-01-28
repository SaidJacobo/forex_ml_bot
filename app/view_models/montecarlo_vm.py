from typing import List
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from app.view_models.metric_warehouse_vm import MetricWarehouseVM


class MontecarloVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: UUID
    BotPerformanceId: UUID
    Simulations: int
    ThresholdRuin: float
    Metrics: List[MetricWarehouseVM]
    