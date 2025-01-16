

from typing import List
import yaml
from app.backbone.database.db_service import DbService
from app.backbone.entities.bot import Bot
from app.backbone.entities.bot_performance import BotPerformance
from app.backbone.entities.bot_trade_performance import BotTradePerformance
from app.backbone.entities.strategy import Strategy
from app.backbone.entities.ticker import Ticker
from app.backbone.entities.timeframe import Timeframe
from pandas import Timestamp
from app.backbone.entities.trade import Trade
from app.backbone.services.operation_result import OperationResult
from app.backbone.services.bot_service import BotService
from app.backbone.utils.get_data import get_data
from app.backbone.utils.general_purpose import load_function
from app.backbone.utils.wfo_utils import run_strategy
import pandas as pd
from pandas import DataFrame

def _performance_from_df_to_obj(df_performance: DataFrame, date_from, date_to, risk, method, bot):
    print(df_performance)
    performance_for_db = [BotPerformance(**row) for _, row in df_performance.iterrows()].pop()
    performance_for_db.DateFrom = date_from
    performance_for_db.DateTo = date_to
    performance_for_db.Risk = risk
    performance_for_db.Method = method
    performance_for_db.Bot = bot # Clave foranea con Bot
    
    return performance_for_db

class BacktestService:
    def __init__(self):
        self.db_service = DbService()
        self.bot_service = BotService()
    
    
    def run(
        self,
        initial_cash: float,
        strategy: Strategy,
        tickers: List[Ticker],
        timeframes: List[Timeframe],
        date_from: Timestamp,
        date_to: Timestamp,
        method: str,
        metatrader_name: str,
        risk: float,
    ):
        
        strategy_path = 'app.backbone.strategies.' + strategy.Name
        strategy_func = load_function(strategy_path)
        
        with open("./configs/leverages.yml", "r") as file_name:
            leverages = yaml.safe_load(file_name)
        
        symbols = {}
        stats_per_symbol = {}
        
        for ticker in tickers:
            leverage = leverages[ticker.Name]
            margin = 1 / leverage
            
            for timeframe in timeframes:
                # try:
                    
                # Se fija si el bot existe para no correrlo de nuevo
                result = self.bot_service.get_bot(
                    strategy_id=strategy.Id,
                    ticker_id=ticker.Id,
                    timeframe_id=timeframe.Id,
                    risk=risk   
                )
                
                if result.ok and result.item:
                    # aca deberia guardar que el bot existe en algun lado y retornar ese mensaje al front
                    print('El bot ya existe')
                    continue
                
                prices = get_data(ticker.Name, timeframe.MetaTraderNumber, date_from, date_to)
                
                prices.index = pd.to_datetime(prices.index)

                if ticker not in symbols.keys():
                    symbols[ticker] = {}
                
                symbols[ticker][timeframe.Name] = prices

                print(f'{ticker.Name}_{timeframe.Name}_{timeframe.Name}')
                
                if ticker not in stats_per_symbol.keys():
                    stats_per_symbol[ticker] = {}
                    
                performance, trade_performance, stats = run_strategy(
                    strategy=strategy_func,
                    ticker=ticker.Name,
                    interval=timeframe.Name,
                    commission=ticker.Commission,
                    prices=prices,
                    initial_cash=initial_cash,
                    margin=margin,
                    risk=risk,
                    plot=False,
                )

                stats_per_symbol[ticker][ticker.Name] = stats                 
                    
                strategy_name = strategy.Name.split(".")[1]
                bot = Bot(
                    Name = f'{strategy_name}_{ticker.Name}_{timeframe.Name}_{risk}',
                    StrategyId = strategy.Id,
                    TickerId = ticker.Id,
                    TimeframeId = timeframe.Id,
                    MetaTraderName = metatrader_name,
                    Risk = risk
                )

                bot_performance_for_db = _performance_from_df_to_obj(performance, date_from, date_to, risk, method, bot)
                
                trade_performance_for_db = [BotTradePerformance(**row) for _, row in trade_performance.iterrows()].pop()
                trade_performance_for_db.BotPerformance = bot_performance_for_db # Clave foranea con BotPerformance
                
                with self.db_service.get_database() as db: # se crea todo de un saque para que haya un unico commit
                    self.db_service.create(db, bot)
                    self.db_service.create(db, bot_performance_for_db)
                    self.db_service.create(db, trade_performance_for_db)
                    
                    trade_history = [Trade(**row) for _, row in stats._trades.iterrows()]
                    for trade in trade_history:
                        trade.BotPerformance = bot_performance_for_db
                        self.db_service.create(db, trade)
                
                # except Exception as e:
                #     strategy_name = strategy.Name.split(".")[1]
                #     name = f'{strategy_name}_{ticker.Name}_{timeframe.Name}_{risk}',
                #     print(f'No se pudo correr la configuracion {name}: {e}')
                    
                       
    def get_performances_by_strategy_ticker(self, strategy_id, ticker_id) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                bot_performances = (
                    db.query(BotPerformance)
                    .join(Bot, Bot.Id == BotPerformance.BotId)
                    .filter(Bot.TickerId == ticker_id)
                    .filter(Bot.StrategyId == strategy_id)
                    .all()
                )   
                
                result = OperationResult(ok=True, message='', item=bot_performances)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
     
    def get_performance_by_bot(self, bot_id) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                bot_performance = self.db_service.get_by_filter(db, BotPerformance, BotId=bot_id)  
                
                result = OperationResult(ok=True, message='', item=bot_performance)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
           
        