

import os
from typing import List
from uuid import UUID
import numpy as np
from sklearn.linear_model import LinearRegression
import yaml
from app.backbone.database.db_service import DbService
from app.backbone.entities.bot import Bot
from app.backbone.entities.bot_performance import BotPerformance
from app.backbone.entities.bot_trade_performance import BotTradePerformance
from app.backbone.entities.luck_test import LuckTest
from app.backbone.entities.metric_wharehouse import MetricWharehouse
from app.backbone.entities.montecarlo_test import MontecarloTest
from app.backbone.entities.random_test import RandomTest
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
from sqlalchemy.orm import joinedload
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import String, func, desc, cast, Uuid


def _performance_from_df_to_obj(
    df_performance: DataFrame, 
    date_from, 
    date_to, 
    risk, 
    method, 
    bot, 
    initial_cash, 
    metatrader_name
    ):
    performance_for_db = [BotPerformance(**row) for _, row in df_performance.iterrows()].pop()
    performance_for_db.DateFrom = date_from
    performance_for_db.DateTo = date_to
    performance_for_db.Risk = risk
    performance_for_db.Method = method
    performance_for_db.Bot = bot
    performance_for_db.InitialCash = initial_cash
    performance_for_db.MetaTraderName = metatrader_name
    
    return performance_for_db

def get_trade_df_from_db(trades: List[Trade], performance_id):
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
            'TopBest': trade.TopBest,
            'TopWorst': trade.TopWorst,
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

                    bot_performance_for_db = _performance_from_df_to_obj(
                        performance, 
                        date_from, 
                        date_to, 
                        risk, 
                        method, 
                        bot,
                        initial_cash,
                        metatrader_name
                    )
                    
                    trade_performance_for_db = [BotTradePerformance(**row) for _, row in trade_performance.iterrows()].pop()
                    trade_performance_for_db.BotPerformance = bot_performance_for_db # Clave foranea con BotPerformance
                    
                    with self.db_service.get_database() as db: # se crea todo de un saque para que haya un unico commit
                        
                        if not result_bot.item:
                            self.db_service.create(db, bot)
                            
                        self.db_service.create(db, bot_performance_for_db)
                        self.db_service.create(db, trade_performance_for_db)
                        
                        trade_history = [Trade(**row) for _, row in stats._trades.iterrows()]
                        for trade in trade_history:
                            trade.BotPerformance = bot_performance_for_db
                            self.db_service.create(db, trade)
                    
                except Exception as e:
                    return OperationResult(ok=False, message=str(e), item=None)
                    
    def get_performances_by_strategy_ticker(self, strategy_id, ticker_id) -> OperationResult:
        with self.db_service.get_database() as db:
            try:
                bot_performances = (
                    db.query(BotPerformance)
                    .join(Bot, Bot.Id == BotPerformance.BotId)
                    .filter(Bot.TickerId == ticker_id)
                    .filter(Bot.StrategyId == strategy_id)
                    .order_by(desc(BotPerformance.CustomMetric))
                    .all()
                )
                result = OperationResult(ok=True, message='', item=bot_performances)
                return result
            except Exception as e:
                result = OperationResult(ok=False, message=str(e), item=None)
                return result
            
    def get_performances_by_bot_dates(self, bot_id, date_from, date_to) -> OperationResult:
        with self.db_service.get_database() as db:
            try:
                bot_performance = (
                    db.query(BotPerformance)
                    .options(
                        joinedload(BotPerformance.RandomTest).joinedload(RandomTest.RandomTestPerformance),
                        joinedload(BotPerformance.LuckTest).joinedload(LuckTest.LuckTestPerformance),
                    )
                    .filter(BotPerformance.BotId == bot_id)
                    .filter(BotPerformance.DateFrom == date_from)
                    .filter(BotPerformance.DateTo == date_to)
                    .first()
                )
                
                result = OperationResult(ok=True, message='', item=bot_performance)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=str(e), item=None)
                return result
     
    def get_performance_by_bot(self, bot_id) -> OperationResult: # cambiar bot_id por backtest_id
        with self.db_service.get_database() as db:
            
            try:
                bot_performance = self.db_service.get_by_filter(db, BotPerformance, BotId=bot_id)  
                
                result = OperationResult(ok=True, message='', item=bot_performance)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=str(e), item=None)
                return result
            
    def get_bot_performance_by_id(self, bot_performance_id) -> OperationResult: # cambiar bot_id por backtest_id
        with self.db_service.get_database() as db:
            
            try:
                bot_performance = self.db_service.get_by_id(db, BotPerformance, id=bot_performance_id)  
                
                result = OperationResult(ok=True, message='', item=bot_performance)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=str(e), item=None)
                return result
           
    def run_montecarlo_test(self, bot_performance_id, n_simulations, threshold_ruin) -> OperationResult:
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
                initial_equity=performance.InitialCash,
                threshold_ruin=threshold_ruin,
                return_raw_curves=False,
                percentiles=[0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95],
            )

            mc = mc.round(3).reset_index().rename(
                columns={'index':'metric'}
            )
            
            mc_long = mc.melt(id_vars=['metric'], var_name='ColumnName', value_name='Value')
            
            montecarlo_test = MontecarloTest(
                BotPerformanceId=performance.Id,
                Simulations=n_simulations,
                ThresholdRuin=threshold_ruin,
            )
            
            rows = [
                MetricWharehouse(
                    Method='Montecarlo', 
                    Metric=row['metric'], 
                    ColumnName=row['ColumnName'], 
                    Value=row['Value'],
                    MontecarloTest=montecarlo_test
                )
                
                for _, row in mc_long.iterrows()
            ]
            
            with self.db_service.get_database() as db:
                self.db_service.create(db, montecarlo_test)
                self.db_service.create_all(db, rows)
            
            return OperationResult(ok=True, message='', item=rows)
        
        except Exception as e:
            
            return OperationResult(ok=False, message=str(e), item=None)
      
    def get_luck_test_equity_curve(self, bot_performance_id, remove_only_good_luck=False) -> OperationResult:
        ''' filtra los mejores y peores trades de un bt y devuelve una nueva curva de equity'''
        result = self.get_bot_performance_by_id(bot_performance_id=bot_performance_id)
        
        if not result.ok:
            return result
            
        try:
            performance = result.item
            
            trades = get_trade_df_from_db(performance.TradeHistory, performance_id=performance.Id)
            
            if remove_only_good_luck:
                filtered_trades = trades[(trades['TopBest'].isna())].sort_values(by='ExitTime')
            
            else:
                filtered_trades = trades[(trades['TopBest'].isna()) & (trades['TopWorst'].isna())].sort_values(by='ExitTime')
            
            filtered_trades['Equity'] = 0
            
            filtered_trades['Equity'] = (performance.InitialCash * (1 + filtered_trades.ReturnPct).cumprod()).round(3)

            equity = filtered_trades[['ExitTime','Equity']]
            
            return OperationResult(ok=True, message=None, item=equity)
        
        except Exception as e:    
            return OperationResult(ok=False, message=str(e), item=None)
            
    def run_luck_test(self, bot_performance_id, trades_percent_to_remove) -> OperationResult:
        
        result = self.get_bot_performance_by_id(bot_performance_id=bot_performance_id)
        if not result.ok:
            return result
        
        try:
            performance = result.item
        
            trades = get_trade_df_from_db(performance.TradeHistory, performance_id=performance.Id)

            trades_to_remove = round((trades_percent_to_remove/100) * trades.shape[0])
            
            top_best_trades = trades.sort_values(by='ReturnPct', ascending=False).head(trades_to_remove)
            top_worst_trades = trades.sort_values(by='ReturnPct', ascending=False).tail(trades_to_remove)
            
            filtered_trades = trades[
                (~trades['Id'].isin(top_best_trades.Id))
                & (~trades['Id'].isin(top_worst_trades.Id))
                & (~trades['ReturnPct'].isna())
            ].sort_values(by='ExitTime')

            filtered_trades['Equity'] = 0
            filtered_trades['Equity'] = (performance.InitialCash * (1 + filtered_trades.ReturnPct).cumprod()).round(3)
            
            dd = np.abs(max_drawdown(filtered_trades['Equity'])).round(3)
            ret = ((filtered_trades.iloc[-1]['Equity'] - filtered_trades.iloc[0]['Equity']) / filtered_trades.iloc[0]['Equity']) * 100
            ret = round(ret, 3)
            
            ret_dd = (ret / dd).round(3)
            custom_metric = ((ret / (1 + dd)) * np.log(1 + filtered_trades.shape[0])).round(3)
            
            x = np.arange(filtered_trades.shape[0]).reshape(-1, 1)
            reg = LinearRegression().fit(x, filtered_trades['Equity'])
            stability_ratio = round(reg.score(x, filtered_trades['Equity']), 3)
            new_winrate = round(
                (filtered_trades[filtered_trades['PnL']>0]['Id'].size / filtered_trades['Id'].size) * 100, 3
            )
            
            luck_test_performance = BotPerformance(**{
                'DateFrom': performance.DateFrom,
                'DateTo': performance.DateTo,
                'BotId': None,
                'StabilityRatio': stability_ratio,
                'Trades': filtered_trades['Id'].size,
                'Return': ret,
                'Drawdown': dd,
                'RreturnDd': ret_dd,
                'WinRate': new_winrate,
                'Duration': performance.Duration,
                'CustomMetric': custom_metric,
                'Method': 'luck_test',
                'InitialCash': performance.InitialCash
            })
            
            luck_test = LuckTest(**{
                'BotPerformanceId': performance.Id,
                'TradesPercentToRemove': trades_percent_to_remove,
                'LuckTestPerformance': luck_test_performance
            })
            
            top_best_trades_id = top_best_trades['Id'].values
            top_worst_trades_id = top_worst_trades['Id'].values
            
            with self.db_service.get_database() as db:
                
                for trade in performance.TradeHistory:
                    if trade.Id in top_best_trades_id:
                        trade.TopBest = True
                        
                    if trade.Id in top_worst_trades_id:
                        trade.TopWorst = True
                    
                    _ = self.db_service.update(db, Trade, trade)
                
                luck_test_db = self.db_service.create(db, luck_test)
                _ = self.db_service.create(db, luck_test_performance)
            
            self._create_luck_test_plot(bot_performance_id=bot_performance_id)
        
            return OperationResult(ok=True, message=None, item=luck_test_db)

        except Exception as e:
            
            return OperationResult(ok=False, message=str(e), item=None)
  
    def _create_luck_test_plot(self, bot_performance_id) -> OperationResult:
        print('Creando grafico de luck test')
        result = self.get_bot_performance_by_id(bot_performance_id=bot_performance_id)
        if not result.ok:
            return result
        
        print('Bot performance obtenida correctamente')
        bot_performance = result.item
        bot_performance.TradeHistory = sorted(bot_performance.TradeHistory, key=lambda trade: trade.ExitTime)


        # Equity plot
        dates = [trade.ExitTime for trade in bot_performance.TradeHistory]
        equity = [trade.Equity for trade in bot_performance.TradeHistory]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=equity,
                            mode='lines',
                            name='Equity'))


        print('Calculando curva de luck test')
        result = self.get_luck_test_equity_curve(bot_performance_id)
        # if not result.ok:
        #     return result

        luck_test_equity_curve = result.item
        print(luck_test_equity_curve)
        
        print('Calculando curva de luck test (BL)')
        result = self.get_luck_test_equity_curve(bot_performance_id, remove_only_good_luck=True)
        if not result.ok:
            return result
        
        luck_test_remove_only_good = result.item
    
        fig.add_trace(go.Scatter(x=luck_test_equity_curve.ExitTime, y=luck_test_equity_curve.Equity,
                            mode='lines',
                            name=f'Luck test'))
        
        fig.add_trace(go.Scatter(x=luck_test_remove_only_good.ExitTime, y=luck_test_remove_only_good.Equity,
                            mode='lines',
                            name=f'Luck test (BL)'))

        fig.update_layout(
            xaxis_title='Time',
            yaxis_title='Equity'
        )   
        
        str_date_from = str(bot_performance.DateFrom).replace('-','')
        str_date_to = str(bot_performance.DateFrom).replace('-','')
        file_name=f'{bot_performance.Bot.Name}_{str_date_from}_{str_date_to}.html'
        
        print('Guardando grafico')
        
        plot_path = './app/templates/static/luck_test_plots'
        
        if not os.path.exists(plot_path):
            os.mkdir(plot_path)

        json_content = fig.to_json()

        with open(os.path.join(plot_path, file_name), 'w') as f:
            f.write(json_content)
            
    def run_random_test(self, bot_performance_id, n_iterations) -> OperationResult:
        result = self.get_bot_performance_by_id(bot_performance_id=bot_performance_id)
        if not result.ok:
            return result
            
        bot_performance = result.item
        ticker = bot_performance.Bot.Ticker
        timeframe = bot_performance.Bot.Timeframe
        
        try:
            with open("./configs/leverages.yml", "r") as file_name:
                leverages = yaml.safe_load(file_name)
                
            leverage = leverages[ticker.Name]
            
            strategy_path = 'app.backbone.strategies.random_trader.RandomTrader'
            
            strategy_func = load_function(strategy_path)
            
            trade_history = get_trade_df_from_db(
                bot_performance.TradeHistory, 
                performance_id=bot_performance.Id
            )
            
            long_trades = trade_history[trade_history['Size'] > 0]
            short_trades = trade_history[trade_history['Size'] < 0]
            
            prices = get_data(
                ticker.Name, 
                timeframe.MetaTraderNumber, 
                pd.Timestamp(bot_performance.DateFrom, tz="UTC"), 
                pd.Timestamp(bot_performance.DateTo, tz="UTC")
            )
            
            prices.index = pd.to_datetime(prices.index)
            
            prob_trade = len(trade_history) / len(prices)  # Probabilidad de realizar un trade
            prob_long = len(long_trades) / len(trade_history) if len(trade_history) > 0 else 0
            prob_short = len(short_trades) / len(trade_history) if len(trade_history) > 0 else 0
           
            trade_history["Duration"] = pd.to_timedelta(trade_history["Duration"])
            trade_history["Bars"] = trade_history["ExitBar"] - trade_history["EntryBar"]

            avg_trade_duration = trade_history.Bars.mean()
            std_trade_duration = trade_history.Bars.std()

            params = {
                'prob_trade': prob_trade,
                'prob_long': prob_long,
                'prob_short': prob_short,
                'avg_trade_duration': avg_trade_duration,
                'std_trade_duration': std_trade_duration,
            }
            
            mean_performance = pd.DataFrame()
            mean_trade_performance = pd.DataFrame()
            
            for _ in range(0, n_iterations):
                performance, trade_performance, stats = run_strategy(
                    strategy=strategy_func,
                    ticker=ticker.Name,
                    risk=bot_performance.Bot.Risk,
                    commission=ticker.Commission,
                    prices=prices,
                    initial_cash=bot_performance.InitialCash,
                    margin=1 / leverage, 
                    opt_params=params
                )

                mean_performance = pd.concat([mean_performance, performance])
                mean_trade_performance = pd.concat([mean_trade_performance, trade_performance])
                
            mean_performance = mean_performance.mean().round(3).to_frame().T
            mean_trade_performance = mean_trade_performance.mean().round(3).to_frame().T
            
            random_test_performance_for_db = _performance_from_df_to_obj(
                df_performance=mean_performance,
                date_from=bot_performance.DateFrom,
                date_to=bot_performance.DateTo,
                risk=bot_performance.Bot.Risk,
                method='random_test',
                bot=None,
                initial_cash=bot_performance.InitialCash,
                metatrader_name=None
            )

            random_test_trade_performance_for_db = [BotTradePerformance(**row) for _, row in mean_trade_performance.iterrows()].pop()

            with self.db_service.get_database() as db:
                # Primero, guardar random_test_performance_for_db
                random_test_performance_for_db = self.db_service.create(db, random_test_performance_for_db)
                
                # Ahora que tenemos el ID, podemos asignarlo a random_test
                random_test = RandomTest(
                    Iterations=n_iterations,
                    BotPerformanceId=bot_performance.Id,
                    RandomTestPerformance=random_test_performance_for_db  # Asignar el ID después de guardar
                )
                
                # Guardar random_test ahora con la relación correcta
                self.db_service.create(db, random_test)

                # Ahora guardar random_test_trade_performance_for_db con las relaciones correctas
                random_test_trade_performance_for_db.BotPerformance = random_test_performance_for_db
                random_test_trade_performance_for_db.BotPerformanceId = random_test_performance_for_db.Id
                random_test_trade_performance_for_db.RandomTest = random_test
                self.db_service.create(db, random_test_trade_performance_for_db)
                
            return OperationResult(ok=True, message=None, item=None)

        except Exception as e:
            
            return OperationResult(ok=False, message=str(e), item=None)
   
    def run_correlation_test(self, bot_performance_id) -> OperationResult:
        
        result = self.get_bot_performance_by_id(bot_performance_id=bot_performance_id)
        if not result.ok:
            return result
        
        try:
            bot_performance = result.item
            
            trade_history = get_trade_df_from_db(
                bot_performance.TradeHistory, 
                performance_id=bot_performance.Id
            )
            
            prices = get_data(
                bot_performance.Bot.Ticker.Name, 
                bot_performance.Bot.Timeframe.MetaTraderNumber, 
                pd.Timestamp(bot_performance.DateFrom, tz="UTC"), 
                pd.Timestamp(bot_performance.DateTo, tz="UTC")
            )

            # Transformar el índice al formato mensual
            equity = trade_history[['ExitTime', 'Equity']]
                    
            equity['month'] = pd.to_datetime(equity['ExitTime']).dt.to_period('M')
            equity = equity.groupby(by='month').agg({'Equity': 'last'})
            equity['perc_diff'] = (equity['Equity'] - equity['Equity'].shift(1)) / equity['Equity'].shift(1)
            equity.fillna(0, inplace=True)

            # Crear un rango completo de meses con PeriodIndex
            full_index = pd.period_range(start=equity.index.min(), end=equity.index.max(), freq='M')

            # Reindexar usando el rango completo de PeriodIndex
            equity = equity.reindex(full_index)
            equity = equity.ffill()

            prices['month'] = pd.to_datetime(prices.index)
            prices['month'] = prices['month'].dt.to_period('M')
            prices = prices.groupby(by='month').agg({'Close':'last'})
            prices['perc_diff'] = (prices['Close'] - prices['Close'].shift(1)) / prices['Close'].shift(1)
            prices.fillna(0, inplace=True)

            prices = prices[prices.index.isin(equity.index)]

            x = np.array(prices['perc_diff']).reshape(-1, 1)
            y = equity['perc_diff']

            # Ajustar el modelo de regresión lineal
            reg = LinearRegression().fit(x, y)
            determination = reg.score(x, y)
            correlation = np.corrcoef(prices['perc_diff'], equity['perc_diff'])[0, 1]

            # Predicciones para la recta
            x_range = np.linspace(x.min(), x.max(), 100).reshape(-1, 1)  # Rango de X para la recta
            y_pred = reg.predict(x_range)  # Valores predichos de Y

            result = pd.DataFrame({
                'correlation': [correlation],
                'determination': [determination],
            }).round(3)

            # Crear el gráfico
            fig = px.scatter(
                x=prices['perc_diff'], y=equity['perc_diff'],
            )

            # Agregar la recta de regresión
            fig.add_scatter(x=x_range.flatten(), y=y_pred, mode='lines', name='Regresión Lineal')

            # Personalización
            fig.update_layout(
                xaxis_title='Monthly Price Variation',
                yaxis_title='Monthly Returns'
            )

            # Agregar anotación con los valores R² y Pearson
            fig.add_annotation(
                x=0.95,  # Posición en el gráfico (en unidades de fracción del eje)
                y=0.95,
                xref='paper', yref='paper',
                text=f"<b>r = {correlation:.3f}<br>R² = {determination:.3f}</b>",
                showarrow=False,
                font=dict(size=16, color="black"),
                align="left",
                bordercolor="black",
                borderwidth=1,
                borderpad=4,
                bgcolor="white",
                opacity=0.8
            )

            str_date_from = str(bot_performance.DateFrom).replace('-','')
            str_date_to = str(bot_performance.DateFrom).replace('-','')
            file_name=f'{bot_performance.Bot.Name}_{str_date_from}_{str_date_to}.html'
            
            plot_path='./app/templates/static/correlation_plots'
            
            if not os.path.exists(plot_path):
                os.mkdir(plot_path)

            json_content = fig.to_json()

            with open(os.path.join(plot_path, file_name), 'w') as f:
                f.write(json_content)
            
            return OperationResult(ok=True, message=False, item=result)

        except Exception as e:
            
            return OperationResult(ok=False, message=str(e), item=None)

    def delete(self, bot_performance_id) -> OperationResult:
        try:
            with self.db_service.get_database() as db:
                # Obtener el BotPerformance a eliminar
                bot_performance = self.db_service.get_by_id(db, BotPerformance, bot_performance_id)

                if not bot_performance:
                    return OperationResult(ok=False, message="BotPerformance no encontrado", item=None)

                bot_trade_performance = self.db_service.get_by_filter(db, BotTradePerformance, BotPerformanceId=bot_performance_id)
                self.db_service.delete(db, BotTradePerformance, bot_trade_performance.Id)
                
                # Eliminar dependencias de MetricsWarehouse relacionadas con MontecarloTests
                montecarlo_test = self.db_service.get_by_filter(db, MontecarloTest, BotPerformanceId=bot_performance_id)
                if montecarlo_test:
                    self.db_service.get_many_by_filter(db, MetricWharehouse, MontecarloTestId=montecarlo_test.Id).delete()
                    self.db_service.delete(db, MontecarloTest, montecarlo_test.Id)

                # Eliminar registros en LuckTest y su relación con LuckTestPerformanceId
                luck_tests = self.db_service.get_many_by_filter(db, LuckTest, BotPerformanceId=bot_performance_id)
                for luck_test in luck_tests:
                    self.db_service.delete(db, BotPerformance, luck_test.LuckTestPerformanceId)
                    self.db_service.delete(db, LuckTest, luck_test.Id)
                    
                str_date_from = str(bot_performance.DateFrom).replace('-','')
                str_date_to = str(bot_performance.DateFrom).replace('-','')
                file_name = f'{bot_performance.Bot.Name}_{str_date_from}_{str_date_to}.html'
                plot_path = './app/templates/static/'
                
                if os.path.exists(os.path.join(plot_path, 'luck_test_plots', file_name)):
                    os.remove(os.path.join(plot_path, 'luck_test_plots', file_name))

                if os.path.exists(os.path.join(plot_path, 'correlation_plots', file_name)):
                    os.remove(os.path.join(plot_path, 'correlation_plots', file_name))
                    
                # Eliminar registros en RandomTest y su relación con RandomTestPerformanceId
                random_tests = self.db_service.get_many_by_filter(db, RandomTest, BotPerformanceId=bot_performance_id)
                for random_test in random_tests:
                    random_test_performance = self.db_service.get_by_id(db, BotPerformance, random_test.RandomTestPerformanceId)
                    random_test_trade_performance = self.db_service.get_by_filter(db, BotTradePerformance, BotPerformanceId=random_test_performance.Id)
                    
                    self.db_service.delete(db, BotTradePerformance, random_test_trade_performance.Id)
                    self.db_service.delete(db, BotPerformance, random_test.RandomTestPerformanceId)
                    self.db_service.delete(db, RandomTest, random_test.Id)


                # Eliminar dependencias directas de la tabla Trade
                self.db_service.get_many_by_filter(db, Trade, BotPerformanceId=bot_performance_id).delete()

                # Verificar si el Bot asociado tiene más BotPerformances
                bot_id = bot_performance.BotId
                if bot_id:
                    remaining_performances = self.db_service.get_many_by_filter(db, BotPerformance, BotId=bot_id).count()

                    # Si no tiene más BotPerformances, eliminar el Bot
                    if remaining_performances == 1:  # Este será eliminado después
                        self.db_service.delete(db, Bot, bot_id)

                # Finalmente eliminar el BotPerformance
                self.db_service.delete(db, BotPerformance, bot_performance_id)

                # Confirmar los cambios
                self.db_service.save(db)

            return OperationResult(ok=True, message="BotPerformance y elementos relacionados eliminados", item=None)

        except Exception as e:
            return OperationResult(ok=False, message=str(e), item=None)

    def get_robusts_by_strategy_id(self, strategy_id) -> OperationResult:
        try:
            with self.db_service.get_database() as db:
                subquery = (
                    db.query(
                        cast(func.min(cast(BotPerformance.Id, String)), Uuid).label("Id"),
                        func.avg(BotPerformance.RreturnDd).label("AVGRreturnDd"),
                        func.max(BotPerformance.RreturnDd).label("MaxRreturnDd"),
                    )
                    .join(Bot, Bot.Id == BotPerformance.BotId)
                    .filter(
                        Bot.StrategyId == strategy_id,
                        BotPerformance.RreturnDd != "NaN",
                    )
                    .group_by(BotPerformance.BotId, BotPerformance.Method)
                    .having(func.avg(BotPerformance.RreturnDd) >= 1)
                    .subquery()
                )

                # Query principal uniendo con la subquery
                query = (
                    db.query(BotPerformance)
                    .join(subquery, BotPerformance.Id == subquery.c.Id)
                ).all()

                return OperationResult(ok=True, message=None, item=query)

        except Exception as e:
            return OperationResult(ok=False, message=str(e), item=None)

    def update_favorite(self, performance_id):
        
        try:
            
            with self.db_service.get_database() as db:
                performance = self.db_service.get_by_id(db, BotPerformance, performance_id)
                
                performance.Favorite = not performance.Favorite
                updated_performance = self.db_service.update(db, BotPerformance, performance)        
                
                return OperationResult(ok=True, message=None, item=updated_performance)
        
        except Exception as e:
            
            return OperationResult(ok=False, message=str(e), item=None)
            

                