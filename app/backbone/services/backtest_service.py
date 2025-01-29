import os
from typing import List
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
from app.backbone.services.utils import _performance_from_df_to_obj
from app.backbone.utils.get_data import get_data
from app.backbone.utils.general_purpose import load_function
from app.backbone.utils.wfo_utils import run_strategy
import pandas as pd
from sqlalchemy.orm import joinedload
from sqlalchemy import func, desc
from sqlalchemy.orm import aliased


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
                    
        return OperationResult(ok=True, message=None, item=None)
    
    
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
        # try:
        with self.db_service.get_database() as db:
            # Subquery para calcular los promedios y máximos de RreturnDd por StrategyId y TickerId
            subquery = (
                db.query(
                    Bot.StrategyId,
                    Bot.TickerId,
                )
                .join(BotPerformance, Bot.Id == BotPerformance.BotId)
                .filter(
                    Bot.StrategyId == strategy_id,
                    BotPerformance.RreturnDd != "NaN",
                )
                .group_by(Bot.StrategyId, Bot.TickerId)
                .having(func.avg(BotPerformance.RreturnDd) > 1)
                .subquery()
            )

            # Alias para evitar ambigüedad en las relaciones
            bot_alias = aliased(Bot)
            bp_alias = aliased(BotPerformance)

            # Query principal con DISTINCT ON
            query = (
                db.query(
                    bp_alias  # Aquí traemos la instancia completa de BotPerformance
                )
                .join(bot_alias, bot_alias.Id == bp_alias.BotId)  # Relacionamos Bot con BotPerformance
                .join(subquery, (bot_alias.StrategyId == subquery.c.StrategyId) & (bot_alias.TickerId == subquery.c.TickerId))
                .order_by(bot_alias.StrategyId, bot_alias.TickerId, bp_alias.CustomMetric.desc())
                .distinct(bot_alias.StrategyId, bot_alias.TickerId)  # DISTINCT ON en SQLAlchemy
            ).all()

            return OperationResult(ok=True, message=None, item=query)

        # except Exception as e:
        #     return OperationResult(ok=False, message=str(e), item=None)

    def update_favorite(self, performance_id):
        
        try:
            
            with self.db_service.get_database() as db:
                performance = self.db_service.get_by_id(db, BotPerformance, performance_id)
                
                performance.Favorite = not performance.Favorite
                updated_performance = self.db_service.update(db, BotPerformance, performance)        
                
                return OperationResult(ok=True, message=None, item=updated_performance)
        
        except Exception as e:
            
            return OperationResult(ok=False, message=str(e), item=None)
            

                