import numpy as np
import pandas as pd
from sqlalchemy import UUID
from app.backbone.entities.portfolio import Portfolio
from app.backbone.entities.portfolio_backtest import PortfolioBacktest
from app.backbone.services.backtest_service import BacktestService
from backbone.database.db_service import DbService
from backbone.services.operation_result import OperationResult
from backbone.services.utils import calculate_margin_metrics, calculate_stability_ratio, ftmo_simulator, get_trade_df_from_db, get_portfolio_equity_curve, max_drawdown
import plotly.graph_objects as go
from collections import namedtuple
    
Metrics = namedtuple('Metrics',['stability_ratio','return_','dd', 'return_dd'])

class PortfolioService:
    def __init__(self):
        self.db_service = DbService()
        self.backtest_service = BacktestService()
        
    def create( self, name:str, description:str) -> OperationResult:
        with self.db_service.get_database() as db:
            
            portfolio_by_filter = self.db_service.get_by_filter(db, Portfolio, Name=name)
            
            if portfolio_by_filter is None:
                
                new_portfolio = Portfolio(Name=name, Description=description)
                
                portfolio = self.db_service.create(db, new_portfolio)

                result = OperationResult(ok=True, message=None, item=portfolio)
                
                return result
            
            result = OperationResult(ok=False, message='El item ya esta cargado en la BD', item=None)
            return result
        
    def get_all(self) -> OperationResult:
        with self.db_service.get_database() as db:
            try:
                all_portfolios = self.db_service.get_all(db, Portfolio)
                result = OperationResult(ok=True, message=None, item=all_portfolios)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
    
    def get_portfolio_by_id(self, portfolio_id:UUID) -> OperationResult:
        with self.db_service.get_database() as db:
            try:
                portfolio = self.db_service.get_by_id(db, Portfolio, id=portfolio_id)
                result = OperationResult(ok=True, message=None, item=portfolio)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
    
    def get_portfolio_backtest(self, portfolio_id:UUID, bot_performance_id:UUID) -> OperationResult:
        with self.db_service.get_database() as db:
            try:
                portfolio_backtest = self.db_service.get_by_filter(
                    db, PortfolioBacktest, PortfolioId=portfolio_id, BotPerformanceId=bot_performance_id
                )
                
                result = OperationResult(ok=True, message=None, item=portfolio_backtest)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result 

    def add_performance(self, portfolio_id:UUID, bot_performance_id:UUID) -> OperationResult:
        result = self.get_portfolio_backtest(portfolio_id=portfolio_id, bot_performance_id=bot_performance_id)
        
        if not result.ok:
            return result
        
        if result.item:
            return OperationResult(ok=False, message='El bot ya fue agregado a este portfolio', item=None)
        
        
        backtest_result = self.backtest_service.get_bot_performance_by_id(bot_performance_id=bot_performance_id)
        portfolio_result = self.get_portfolio_by_id(portfolio_id=portfolio_id)
        
        if not backtest_result.ok:
            return backtest_result
        
        if not portfolio_result.ok:
            return portfolio_result
        
        bot_performance = backtest_result.item
        portfolio = portfolio_result.item
        
        portfolio_backtest = PortfolioBacktest(
            PortfolioId = portfolio.Id,
            BotPerformanceId = bot_performance.Id,
            Portfolio = portfolio,
            BotPerformance = bot_performance
        )
        
        with self.db_service.get_database() as db:
            try:
                new_portfolio_backtest = self.db_service.create(db, portfolio_backtest)
                
                return OperationResult(ok=True, message=None, item=new_portfolio_backtest)
            
            except Exception as e:
            
                result = OperationResult(ok=False, message=str(e), item=None)
                return result        

    def delete_performance(self, portfolio_id:UUID, bot_performance_id:UUID) -> OperationResult:
        result = self.get_portfolio_backtest(portfolio_id=portfolio_id, bot_performance_id=bot_performance_id)
        
        if not result.ok:
            return result
               
        if not result.item:
            return OperationResult(ok=False, message='El bot no fue agregado a este portfolio', item=None)
        
        portfolio_backtest_result = result.item
        
        with self.db_service.get_database() as db:
            try:
                self.db_service.delete(db, PortfolioBacktest, portfolio_backtest_result.Id)
                return OperationResult(ok=True, message=None, item=None)
            
            except Exception as e:
            
                result = OperationResult(ok=False, message=str(e), item=None)
                return result  

    def get_backtests_from_portfolio(self, portfolio_id:UUID) -> OperationResult:
        
        try:
            with self.db_service.get_database() as db:
                portfolio_backtests = self.db_service.get_many_by_filter(db, PortfolioBacktest, PortfolioId=portfolio_id)
                
                backtests = [portfolio_backtest.BotPerformance for portfolio_backtest in portfolio_backtests ]
                
                return OperationResult(ok=True, message=None, item=backtests)
        
        except Exception as e:
            
            return OperationResult(ok=False, message=str(e), item=None)

    def get_df_trades(self, portfolio_id: UUID) -> OperationResult:
        """Obtiene las curvas de equity de cada bot en un portafolio."""
        result = self.get_backtests_from_portfolio(portfolio_id)
        
        if not result.ok:
            return result
        
        try:
            all_backtests = result.item
            trades_with_equity = {
                backtest.Bot.Name: get_trade_df_from_db(backtest.TradeHistory, backtest.Id) 
                for backtest in all_backtests
            }
            
            return OperationResult(ok=True, message=None, item=trades_with_equity)
        
        except Exception as e:
            return OperationResult(ok=False, message=str(e), item=None)

    def get_portfolio_equity_curve(self, equity_curves: dict) -> OperationResult:
        """Calcula la curva de equity del portafolio a partir de las curvas individuales."""
        try:
            eq_curve = get_portfolio_equity_curve(equity_curves=equity_curves, initial_equity=100_000)
            return OperationResult(ok=True, message=None, item=eq_curve)
        
        except Exception as e:
            return OperationResult(ok=False, message=str(e), item=None)
   
    def plot_portfolio_equity_curve(self, equity_curves: pd.DataFrame) -> OperationResult:
        
        try:
            # Crear una figura vacía
            fig = go.Figure()

            # Recorrer las curvas de equity de cada bot y agregarlas al gráfico
            for k, v in equity_curves.items():
                fig.add_trace(go.Scatter(x=v.index, y=v.Equity, mode='lines', name=k))

            # Actualizar los detalles del layout del gráfico
            fig.update_layout(
                xaxis_title="Fecha",
                yaxis_title="Equity",
                legend_title="Bots"
            )

            json_content = fig.to_json()
            
            return OperationResult(ok=True, message=None, item=json_content)
        
        except Exception as e:
            return OperationResult(ok=False, message=str(e), item=None)
            
    def get_portfolio_metrics(self, portfolio_equity_curve: pd.Series) -> OperationResult:
        
        try:
            stability_ratio = round(calculate_stability_ratio(portfolio_equity_curve), 3)
            return_ = round(((portfolio_equity_curve.Equity.iloc[-1] - portfolio_equity_curve.Equity.iloc[0]) / portfolio_equity_curve.Equity.iloc[0]) * 100, 3)
            dd = round(np.abs(max_drawdown(portfolio_equity_curve, verbose=False)), 3)
            return_dd = round(return_ / dd, 3)
            
            portfolio_metrics = Metrics(stability_ratio, return_, dd, return_dd)
            
            return OperationResult(
                ok=True, 
                message=None, 
                item=portfolio_metrics
            )
        
        except Exception as e:
            return OperationResult(ok=False, message=str(e), item=None)
    
    def get_challenge_metrics(self, portfolio_equity_curve: pd.Series) -> OperationResult:
        try:
            challenge_metrics = ftmo_simulator(portfolio_equity_curve, initial_cash=100_000)
            
            return OperationResult(
                ok=True, 
                message=None, 
                item=challenge_metrics
            )
        
        except Exception as e:
            return OperationResult(ok=False, message=str(e), item=None)
        
    def get_margin_metrics(self, all_trades:pd.DataFrame, portfolio_equity_curve:pd.Series) -> OperationResult:
        try:
            margin_metrics = calculate_margin_metrics(all_trades, portfolio_equity_curve)
            
            return OperationResult(
                ok=True, 
                message=None, 
                item=margin_metrics
            )
        
        except Exception as e:
            return OperationResult(ok=False, message=str(e), item=None)