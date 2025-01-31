from sqlalchemy import UUID
from app.backbone.entities.bot import Bot
from backbone.database.db_service import DbService
from backbone.entities.strategy import Strategy
from backbone.services.operation_result import OperationResult

class StrategyService:
    def __init__(self):
        self.db_service = DbService()
        
    def create( self, name:str, description:str) -> OperationResult:
        with self.db_service.get_database() as db:
            
            strategy_by_filter = self.db_service.get_by_filter(db, Strategy, Name=name)
            
            if strategy_by_filter is None:
                
                new_strategy = Strategy(Name=name, Description=description)
                
                strategy = self.db_service.create(db, new_strategy)

                result = OperationResult(ok=True, message=None, item=strategy)
                
                return result
            
            result = OperationResult(ok=False, message='El item ya esta cargado en la BD', item=None)
            return result
    
    def get_all(self) -> OperationResult:
        with self.db_service.get_database() as db:
            
            try:
                all_strategies = self.db_service.get_all(db, Strategy)
                result = OperationResult(ok=True, message=None, item=all_strategies)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
                       
    def delete(self, id) -> OperationResult:
        
       with self.db_service.get_database() as db:
            
            try:
                strategy = self.db_service.delete(db, Strategy, id)
                result = OperationResult(ok=True, message='', item=strategy)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
       
    def get_by_id(self, id) -> OperationResult:
        with self.db_service.get_database() as db:

            try:
                strategy = self.db_service.get_by_id(db, Strategy, id)
                result = OperationResult(ok=True, message='', item=strategy)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
        
    def update(self, id:UUID, name:str, description:str) -> OperationResult:
        
        with self.db_service.get_database() as db:
            try:
                new_strategy = Strategy(Id=id, Name=name, Description=description)
                
                strategy = self.db_service.update(db, Strategy, new_strategy)
                
                result = OperationResult(ok=True, message='', item=strategy)
                return result
                
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
            
    def get_used_strategies(self) -> OperationResult:
        with self.db_service.get_database() as db:
        
            strategies = (
                db.query(Strategy)
                .join(Bot, Strategy.Id == Bot.StrategyId)  # Relación entre Strategy y Bot
                .distinct()  # Evita duplicados
                .all()  # Recupera los resultados
            )
            
            result = OperationResult(ok=True, message='', item=strategies)
            return result
        
