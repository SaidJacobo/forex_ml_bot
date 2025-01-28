from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from app.view_models.ticker_vm import TickerVM

class CategoryVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id:UUID
    Name: str
    Tickers: Optional[List[TickerVM]] = None  # Relación con Tickers