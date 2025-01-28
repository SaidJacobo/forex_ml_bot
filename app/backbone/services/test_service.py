import os
import numpy as np
from sklearn.linear_model import LinearRegression
import yaml
from app.backbone.database.db_service import DbService
from app.backbone.entities.bot_performance import BotPerformance
from app.backbone.entities.bot_trade_performance import BotTradePerformance
from app.backbone.entities.luck_test import LuckTest
from app.backbone.entities.metric_wharehouse import MetricWharehouse
from app.backbone.entities.montecarlo_test import MontecarloTest
from app.backbone.entities.random_test import RandomTest
from app.backbone.entities.trade import Trade
from app.backbone.services.backtest_service import BacktestService
from app.backbone.services.operation_result import OperationResult
from app.backbone.services.utils import _performance_from_df_to_obj, get_trade_df_from_db
from app.backbone.utils.get_data import get_data
from app.backbone.utils.general_purpose import load_function
from app.backbone.utils.montecarlo_utils import max_drawdown, monte_carlo_simulation_v2
from app.backbone.utils.wfo_utils import run_strategy
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go



class TestService:
    
    def __init__(self):
        self.db_service = DbService()
        self.backtest_service = BacktestService()
        
    def run_montecarlo_test(self, bot_performance_id, n_simulations, threshold_ruin) -> OperationResult:
        result = self.backtest_service.get_bot_performance_by_id(bot_performance_id=bot_performance_id)
        
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
        result = self.backtest_service.get_bot_performance_by_id(bot_performance_id=bot_performance_id)
        
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
        
        result = self.backtest_service.get_bot_performance_by_id(bot_performance_id=bot_performance_id)
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
        result = self.backtest_service.get_bot_performance_by_id(bot_performance_id=bot_performance_id)
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
        result = self.backtest_service.get_bot_performance_by_id(bot_performance_id=bot_performance_id)
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
        
        result = self.backtest_service.get_bot_performance_by_id(bot_performance_id=bot_performance_id)
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
