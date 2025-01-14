from pydantic import BaseModel, ConfigDict
from uuid import UUID


class BotVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    Id:UUID
    Name: str