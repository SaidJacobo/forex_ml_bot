import time
from sqlalchemy import UUID
from app.backbone.entities.timeframes import Timeframe
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
            print("initialize() failed, error code =",mt5.last_error())
            quit()

        symbols = mt5.symbols_get()
        
        categories_tickers = {}
        for symbol in symbols:
            category_name = symbol.path.split('\\')[0]
            ticker_name = symbol.path.split('\\')[1]
            
            if category_name not in categories_tickers.keys():
                categories_tickers[category_name] = []
            
            categories_tickers[category_name].append(ticker_name)
           
        
        with self.db_service.get_database() as db:
            
            self.db_service.delete_all(db, Ticker)
            self.db_service.delete_all(db, Category)
            
            for category_name in categories_tickers.keys():
                
                category = Category(Name=category_name)
                
                
                self.db_service.create(db, category)
                
                for ticker_name in categories_tickers[category_name]:
                    print(ticker_name)
                    
                    symbol_info = mt5.symbol_info_tick(ticker_name)
                    
                    if symbol_info != None:
                        
                        print(symbol_info)

                        avg_price = (symbol_info.bid + symbol_info.ask) / 2
                        spread = symbol_info.ask - symbol_info.bid
                        commission = round(spread / avg_price, 5)
                        
                        ticker = Ticker(Name=ticker_name, Category=category, Commission=commission, )
                        self.db_service.create(db, ticker)
                    
                

        
        return OperationResult(ok=True, message='', item=None)

    def get_all(self) -> OperationResult:
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