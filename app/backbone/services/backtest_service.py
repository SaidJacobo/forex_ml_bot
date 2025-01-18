

from typing import List
import numpy as np
from sklearn.linear_model import LinearRegression
import yaml
from app.backbone.database.db_service import DbService
from app.backbone.entities.bot import Bot
from app.backbone.entities.bot_performance import BotPerformance
from app.backbone.entities.bot_trade_performance import BotTradePerformance
from app.backbone.entities.metric_wharehouse import MetricWharehouse
from app.backbone.entities.strategy import Strategy
from app.backbone.entities.ticker import Ticker
from app.backbone.entities.timeframe import Timeframe
from pandas import Timestamp
from app.backbone.entities.trade import Trade
from app.backbone.services.operation_result import OperationResult
from app.backbone.services.bot_service import BotService
from app.backbone.utils.get_data import get_data
from app.backbone.utils.general_purpose import load_function
from app.backbone.utils.montecarlo_utils import max_drawdown, monte_carlo_simulation_v2
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

def get_trade_df_from_db(trades, performance_id):
    data = [{
            'Id': trade.Id,
            'BotPerformanceId': performance_id,
            'Size': trade.Size,
            'EntryBar': trade.EntryBar,
            'ExitBar': trade.ExitBar,
            'EntryPrice': trade.EntryPrice,
            'ExitPrice': trade.ExitPrice,
            'PnL': trade.PnL,
            'ReturnPct': trade.ReturnPct,
            'EntryTime': trade.EntryTime,
            'ExitTime': trade.ExitTime,
            'Duration': trade.Duration,
            'Equity': trade.Equity,
        }
        for trade in trades
    ]
    
    return pd.DataFrame(data)

class BacktestService:
    def __init__(self):
        self.db_service = DbService()
        self.bot_service = BotService()
    
    
    def run_backtest(
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
        strategy_name = strategy.Name.split(".")[1]
        
        with open("./configs/leverages.yml", "r") as file_name:
            leverages = yaml.safe_load(file_name)
        
        symbols = {}
        stats_per_symbol = {}
        
        for ticker in tickers:
            leverage = leverages[ticker.Name]
            margin = 1 / leverage
            
            for timeframe in timeframes:
                
                bot_name = f'{strategy_name}_{ticker.Name}_{timeframe.Name}_{risk}'
                
                # Se fija si el bot existe para no correrlo de nuevo
                result_bot = self.bot_service.get_bot(
                    strategy_id=strategy.Id,
                    ticker_id=ticker.Id,
                    timeframe_id=timeframe.Id,
                    risk=risk   
                )
                
                if not result_bot.ok:
                    return OperationResult(ok=False, message=result_bot.message)
                
                
                bot = None
                if result_bot.item:
                    bot = result_bot.item
                    
                    result_performance = self.get_performances_by_bot_dates(
                        bot_id=bot.Id, 
                        date_from=date_from, 
                        date_to=date_to
                    )
                    
                    if not result_performance.ok:
                        return OperationResult(ok=False, message=result_performance.message)
                    
                    if result_performance.item:
                        continue

                else:
                    bot = Bot(
                        Name = bot_name,
                        StrategyId = strategy.Id,
                        TickerId = ticker.Id,
                        TimeframeId = timeframe.Id,
                        MetaTraderName = metatrader_name,
                        Risk = risk
                    )

                try:
                    prices = get_data(ticker.Name, timeframe.MetaTraderNumber, date_from, date_to)
                    
                    prices.index = pd.to_datetime(prices.index)

                    if ticker not in symbols.keys():
                        symbols[ticker] = {}
                    
                    symbols[ticker][timeframe.Name] = prices

                    print(f'{ticker.Name}_{timeframe.Name}_{risk}')
                    
                    if ticker not in stats_per_symbol.keys():
                        stats_per_symbol[ticker] = {}

                    str_date_from = str(date_from.date()).replace('-','')
                    str_date_to = str(date_to.date()).replace('-','')
                    
                    performance, trade_performance, stats = run_strategy(
                        strategy=strategy_func,
                        ticker=ticker.Name,
                        risk=risk,
                        commission=ticker.Commission,
                        prices=prices,
                        initial_cash=initial_cash,
                        margin=margin,
                        plot_path=f'./app/templates/static/backtest_plots',
                        file_name=f'{bot_name}_{str_date_from}_{str_date_to}.html'
                    )

                    stats_per_symbol[ticker][ticker.Name] = stats                 

                    bot_performance_for_db = _performance_from_df_to_obj(performance, date_from, date_to, risk, method, bot)
                    
                    trade_performance_for_db = [BotTradePerformance(**row) for _, row in trade_performance.iterrows()].pop()
                    trade_performance_for_db.BotPerformance = bot_performance_for_db # Clave foranea con BotPerformance
                    
                    with self.db_service.get_database() as db: # se crea todo de un saque para que haya un unico commit
                        
                        if not result_bot.item:
                            self.db_service.create(db, bot)
                            
                        self.db_service.create(db, bot_performance_for_db)
                        
                        trade_history = [Trade(**row) for _, row in stats._trades.iterrows()]
                        for trade in trade_history:
                            trade.BotPerformance = bot_performance_for_db
                            self.db_service.create(db, trade)
                    
                except Exception as e:
                    return OperationResult(ok=False, message=e)
                    
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
            
    def get_performances_by_bot_dates(self, bot_id, date_from, date_to) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                bot_performance = (
                    db.query(BotPerformance)
                    .filter(BotPerformance.BotId == bot_id)
                    .filter(BotPerformance.DateFrom == date_from)
                    .filter(BotPerformance.DateTo == date_to)
                    .first()
                )   
                
                result = OperationResult(ok=True, message='', item=bot_performance)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
     
    def get_performance_by_bot(self, bot_id) -> OperationResult: # cambiar bot_id por backtest_id
        with self.db_service.get_database() as db:
            
            try:
                bot_performance = self.db_service.get_by_filter(db, BotPerformance, BotId=bot_id)  
                
                result = OperationResult(ok=True, message='', item=bot_performance)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
            
    def get_bot_performance_by_id(self, bot_performance_id) -> OperationResult: # cambiar bot_id por backtest_id
        with self.db_service.get_database() as db:
            
            try:
                bot_performance = self.db_service.get_by_filter(db, BotPerformance, Id=bot_performance_id)  
                
                result = OperationResult(ok=True, message='', item=bot_performance)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
           
    def run_montecarlo_test(self, bot_performance_id, n_simulations, initial_cash, threshold_ruin):
        result = self.get_bot_performance_by_id(bot_performance_id=bot_performance_id)
        
        if not result.ok:
            return OperationResult(ok=False, message=result.message, item=None)
            
        try:
            performance = result.item
            trades_history = get_trade_df_from_db(performance.TradeHistory, performance_id=performance.Id)

            mc = monte_carlo_simulation_v2(
                equity_curve=trades_history.Equity,
                trade_history=trades_history,
                n_simulations=n_simulations,
                initial_equity=initial_cash,
                threshold_ruin=threshold_ruin,
                return_raw_curves=False,
                percentiles=[0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95],
            )

            mc = mc.round(3).reset_index().rename(
                columns={'index':'metric'}
            )
            
            mc_long = mc.melt(id_vars=['metric'], var_name='ColumnName', value_name='Value')
            
            rows = [
                MetricWharehouse(
                    Method='Montecarlo', 
                    Metric=row['metric'], 
                    ColumnName=row['ColumnName'], 
                    Value=row['Value'],
                    BotPerformanceId=performance.Id,
                    BotPerformance=performance
                )
                
                for _, row in mc_long.iterrows()
            ]
            
            with self.db_service.get_database() as db:
                db.add_all(rows)
            
            return OperationResult(ok=True, message='', item=rows)
        
        except Exception as e:
            
            return OperationResult(ok=False, message=e, item=None)
        
    def run_luck_test(self, bot_performance_id, trades_percent_to_remove):
        
        initial_cash = 100_000 # cambiar por bot_performance.initial_cash
        
        result = self.get_bot_performance_by_id(bot_performance_id=bot_performance_id)
        
        if not result.ok:
            return OperationResult(ok=False, message=result.message, item=None)
            
        # try:
        performance = result.item
    
        trades = get_trade_df_from_db(performance.TradeHistory, performance_id=performance.Id)

        trades_to_remove = round((trades_percent_to_remove/100) * trades.shape[0])
        
        top_best_trades = trades.sort_values(by='ReturnPct', ascending=False).head(trades_to_remove)
        top_worst_trades = trades.sort_values(by='ReturnPct', ascending=False).tail(trades_to_remove)
        
        trades_to_remove *= 2
        
        filtered_trades = trades[
            (~trades['Id'].isin(top_best_trades.Id))
            & (~trades['Id'].isin(top_worst_trades.Id))
            & (~trades['ReturnPct'].isna())
        ].sort_values(by='ExitTime')

        filtered_trades['Equity'] = 0
        filtered_trades['Equity'] = initial_cash * (1 + filtered_trades.ReturnPct).cumprod()
        
        dd = -1 * max_drawdown(filtered_trades['Equity'])
        ret = ((filtered_trades.iloc[-1]['Equity'] - filtered_trades.iloc[0]['Equity']) / filtered_trades.iloc[0]['Equity']) * 100
        ret_dd = ret / dd
        custom_metric = (ret / (1 + dd)) * np.log(1 + filtered_trades.shape[0])  
        
        x = np.arange(filtered_trades.shape[0]).reshape(-1, 1)
        reg = LinearRegression().fit(x, filtered_trades['Equity'])
        stability_ratio = reg.score(x, filtered_trades['Equity'])
        
        metrics = pd.DataFrame({
            'strategy': [f'take_off_{trades_to_remove}_trades'],
            # 'ticker': [ticker],
            # 'interval': [interval],
            'stability_ratio': [stability_ratio],
            'return': [ret],
            'drawdown': [dd],
            'return_drawdown': [ret_dd],
            'custom_metric': [custom_metric],
        })
    
        return OperationResult(ok=True, message=None, item=metrics)

        # except Exception as e:
            
        #     return OperationResult(ok=False, message=e, item=None)
            
            # # Create traces
            # fig = go.Figure()
            # fig.add_trace(go.Scatter(x=trades.ExitTime, y=trades.Equity,
            #                     mode='lines',
            #                     name='equity original'))

            # fig.add_trace(go.Scatter(x=filtered_trades.ExitTime, y=filtered_trades.Equity,
            #                     mode='lines',
            #                     name=f'take_of_{trades_to_remove}_trades'))

            # fig.update_layout(
            #     title=f"{strategy_name}_{ticker}_{interval}",
            #     xaxis_title='Time',
            #     yaxis_title='Equity'
            # )     