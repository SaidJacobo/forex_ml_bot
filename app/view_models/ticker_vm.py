from pydantic import BaseModel, ConfigDict
from uuid import UUID

class TickerVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id:UUID
    CategoryId:UUID
    Name: str
    Commission: float