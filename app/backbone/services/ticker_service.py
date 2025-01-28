import time
from sqlalchemy import UUID
from app.backbone.entities.bot import Bot
from app.backbone.entities.strategy import Strategy
from app.backbone.entities.timeframe import Timeframe
from backbone.database.db_service import DbService
from backbone.services.operation_result import OperationResult
from backbone.entities.ticker import Ticker
from backbone.entities.category import Category
import MetaTrader5 as mt5

class TickerService:
    def __init__(self):
        self.db_service = DbService()
        
    def create(self) -> OperationResult:
        if not mt5.initialize():
            print("initialize() failed, error code =", mt5.last_error())
            quit()

        symbols = mt5.symbols_get()

        categories_tickers = {}
        for symbol in symbols:
            category_name = symbol.path.split("\\")[0]
            ticker_name = symbol.path.split("\\")[1]

            if category_name not in categories_tickers.keys():
                categories_tickers[category_name] = []

            categories_tickers[category_name].append(ticker_name)

        with self.db_service.get_database() as db:
            for category_name, tickers in categories_tickers.items():
                # Buscar la categoría en la base de datos
                category = self.db_service.get_by_filter(db, Category, Name=category_name)
                
                # Si la categoría no existe, crearla
                if not category:
                    category = Category(Name=category_name)
                    self.db_service.create(db, category)

                # Procesar los tickers asociados a esta categoría
                for ticker_name in tickers:
                    print(ticker_name)

                    _ = mt5.copy_rates_from_pos(
                        ticker_name, 16385, 0, 3
                    )

                    symbol_info = mt5.symbol_info_tick(ticker_name)

                    if symbol_info is not None:
                        print(symbol_info)

                        avg_price = (symbol_info.bid + symbol_info.ask) / 2

                        if avg_price > 0:
                            spread = symbol_info.ask - symbol_info.bid
                            commission = round(spread / avg_price, 5)

                            # Buscar el ticker en la base de datos
                            ticker = self.db_service.get_by_filter(db, Ticker, Name=ticker_name, CategoryId=category.Id)
                            
                            # Si el ticker no existe, crearlo
                            if not ticker:
                                ticker = Ticker(Name=ticker_name, Category=category, Commission=commission)
                                self.db_service.create(db, ticker)
                            else:
                                # Si el ticker existe, actualizar su información
                                ticker.Commission = commission
                                self.db_service.update(db, Ticker, ticker)

            # Confirmar los cambios en la base de datos
            self.db_service.save(db)

        return OperationResult(ok=True, message="Categorías y tickers procesados correctamente", item=None)


    def get_all_categories(self) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                categories = self.db_service.get_all(db, Category)
                result = OperationResult(ok=True, message='', item=categories)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
                       
    def get_tickers_by_category(self, category_id:UUID) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                tickers = self.db_service.get_many_by_filter(db, Ticker, CategoryId=category_id)
                result = OperationResult(ok=True, message='', item=tickers)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result

    def get_all_categories(self) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                categories = self.db_service.get_all(db, Category)
                result = OperationResult(ok=True, message='', item=categories)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
             
    def get_all_timeframes(self) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                timeframes = self.db_service.get_all(db, Timeframe)
                result = OperationResult(ok=True, message='', item=timeframes)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
            
    def get_ticker_by_id(self, id) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                ticker = self.db_service.get_by_id(db, Ticker, id)
                result = OperationResult(ok=True, message='', item=ticker)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
            
    def get_all_timeframes(self) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                categories = self.db_service.get_all(db, Timeframe)
                result = OperationResult(ok=True, message='', item=categories)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result

    def get_timeframe_by_id(self, id) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                strategy = self.db_service.get_by_id(db, Timeframe, id)
                result = OperationResult(ok=True, message='', item=strategy)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
            
    def get_all_tickers(self) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                tickers = self.db_service.get_all(db, Ticker)
                result = OperationResult(ok=True, message='', item=tickers)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
            
    def get_tickers_by_strategy(self, strategy_id) -> OperationResult:
        with self.db_service.get_database() as db:
        
            strategies = (
                db.query(Ticker)
                    .join(Bot, Bot.TickerId == Ticker.Id)
                    .filter(Bot.StrategyId == strategy_id)
            )
            
            result = OperationResult(ok=True, message='', item=strategies)
            return result