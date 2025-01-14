from app.backbone.database.db_service import DbService
from app.backbone.entities.bot import Bot
from app.backbone.services.operation_result import OperationResult


class BotService:
    def __init__(self):
        self.db_service = DbService()
        
    
    def get_bot_by_strategy(self, strategy_id) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                bots = self.db_service.get_many_by_filter(db, Bot, StrategyId=strategy_id)
                result = OperationResult(ok=True, message='', item=bots)
                
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result