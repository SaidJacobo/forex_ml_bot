from pydantic import BaseModel, ConfigDict
from uuid import UUID

class TimeframeVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id:UUID
    Name: str
    MetaTraderNumber: int