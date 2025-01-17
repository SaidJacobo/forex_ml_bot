from app.backbone.database.db_service import DbService
from app.backbone.entities.bot import Bot
from app.backbone.services.operation_result import OperationResult


class BotService:
    def __init__(self):
        self.db_service = DbService()
        
    
    def get_bots_by_strategy(self, strategy_id) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                bots = self.db_service.get_many_by_filter(db, Bot, StrategyId=strategy_id)
                result = OperationResult(ok=True, message='', item=bots)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
            
    def get_bot(self, strategy_id, ticker_id, timeframe_id, risk) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                bot = self.db_service.get_by_filter(
                    db, 
                    Bot, 
                    StrategyId=strategy_id,
                    TickerId=ticker_id,
                    TimeframeId=timeframe_id,
                    Risk=risk
                )
                
                result = OperationResult(ok=True, message='', item=bot)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
            
    def get_all_bots(self) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                all_bots = self.db_service.get_all(db, Bot)
                result = OperationResult(ok=True, message='', item=all_bots)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
            
    def get_bot_by_id(self, bot_id) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                bot = self.db_service.get_by_id(db, Bot, id=bot_id)
                result = OperationResult(ok=True, message='', item=bot)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result

