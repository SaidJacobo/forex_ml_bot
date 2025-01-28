from typing import List
from pydantic import BaseModel, ConfigDict
from uuid import UUID


class MetricWarehouseVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: UUID
    MontecarloTestId: UUID
    Method: str
    Metric: str
    ColumnName: str
    Value: float