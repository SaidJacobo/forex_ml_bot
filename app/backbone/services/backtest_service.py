

from turtle import pd
from typing import List

import yaml
from app.backbone.database.db_service import DbService
from app.backbone.entities.strategy import Strategy
from app.backbone.entities.ticker import Ticker
from app.backbone.entities.timeframe import Timeframe
from pandas import Timestamp
from app.backbone.utils.get_data import get_data
from app.backbone.utils.general_purpose import load_function
from app.backbone.utils.wfo_utils import run_strategy
import pandas as pd


class BacktestService:
    def __init__(self):
        self.db_service = DbService()
        
    
    def run(
        self,
        initial_cash: float,
        strategy: Strategy,
        tickers: List[Ticker],
        timeframes: List[Timeframe],
        date_from: Timestamp,
        date_to: Timestamp,
        risk: float,
    ):
        
        strategy_path = 'app.backbone.strategies.' + strategy.Name
        strategy = load_function(strategy_path)
        
        with open("./configs/leverages.yml", "r") as file_name:
            leverages = yaml.safe_load(file_name)
        
        performance = pd.DataFrame()
        trade_performances = pd.DataFrame()
        symbols = {}
        stats_per_symbol = {}
        
        for ticker in tickers:
            leverage = leverages[ticker.Name]
            margin = 1 / leverage
            
            for timeframe in timeframes:
                
                prices = get_data(ticker.Name, timeframe.MetaTraderNumber, date_from, date_to)
                
                prices.index = pd.to_datetime(prices.index)

                if ticker not in symbols.keys():
                    symbols[ticker] = {}
                
                symbols[ticker][timeframe.Name] = prices

                print(f'{ticker}_{timeframe.Name}')
                
                if ticker not in stats_per_symbol.keys():
                    stats_per_symbol[ticker] = {}
                    
                df_stats, strategy_trade_performance, stats = run_strategy(
                    strategy=strategy,
                    ticker=ticker.Name,
                    interval=timeframe.Name,
                    commission=ticker.Commission,
                    prices=prices,
                    initial_cash=initial_cash,
                    margin=margin,
                    risk=risk,
                    plot=False,  # enviar ruta de donde quiero que se guarde
                )

                performance = pd.concat([performance, df_stats])
                trade_performances = pd.concat([trade_performances, strategy_trade_performance])
                stats_per_symbol[ticker][ticker.Name] = stats
        
        print(performance)
        
        