from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID


class BotTradePerformamceVM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    Id: UUID
    BotPerformanceId: UUID
    MeanWinningReturnPct: float
    StdWinningReturnPct: float
    MeanLosingReturnPct: float
    StdLosingReturnPct: float
    MeanTradeDuration: float
    StdTradeDuration: float
    
    LongWinrate: float
    WinLongMeanReturnPct: float
    WinLongStdReturnPct: float
    LoseLongMeanReturnPct: float
    LoseLongStdReturnPct: float
    
    ShortWinrate: float
    WinShortMeanReturnPct: float
    WinShortStdReturnPct: float
    LoseShortMeanReturnPct: float
    LoseShortStdReturnPct: float
