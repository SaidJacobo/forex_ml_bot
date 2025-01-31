from sqlalchemy import UUID
from app.backbone.entities.bot import Bot
from app.backbone.entities.portfolio import Portfolio
from app.backbone.entities.portfolio_backtest import PortfolioBacktest
from app.backbone.services.backtest_service import BacktestService
from backbone.database.db_service import DbService
from backbone.entities.strategy import Strategy
from backbone.services.operation_result import OperationResult

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
            
    def get_backtest_from_portfolio(self, portfolio_id:UUID) -> OperationResult:
        
        try:
            with self.db_service.get_database() as db:
                portfolio_backtests = self.db_service.get_many_by_filter(db, PortfolioBacktest, PortfolioId=portfolio_id)
                
                backtests = [portfolio_backtest.BotPerformance for portfolio_backtest in portfolio_backtests ]
                
                return OperationResult(ok=True, message=None, item=backtests)
        
        except Exception as e:
            return OperationResult(ok=False, message=str(e), item=None)
            