

from typing import List
from app.backbone.database.db_service import DbService
from app.backbone.entities.strategy import Strategy
from app.backbone.entities.ticker import Ticker
from app.backbone.entities.timeframe import Timeframe
from pandas import Timestamp


class BacktestService:
    def __init__(self):
        self.db_service = DbService()
        
    
    def run(
        self,
        strategy:Strategy,
        tickers: List[Ticker],
        timeframes: List[Timeframe],
        date_from: Timestamp,
        date_to: Timestamp,
        risk: float,
    ):
        
        
        print('entro al servicio')