from sqlalchemy import UUID
from backbone.database.crud import CRUDBase
from backbone.entities.strategy import Strategy
from backbone.services.operation_result import OperationResult

class StrategyService:
    def __init__(self):
        self.crud = CRUDBase(Strategy)
        
    def create( self, name:str, description:str) -> OperationResult:
        with self.crud.get_database() as db:
            
            strategy_by_filter = self.crud.get_by_filter(db, Name=name)
            
            if strategy_by_filter is None:
                
                new_strategy = Strategy(Name=name, Description=description)
                
                strategy = self.crud.create(db, new_strategy)

                result = OperationResult(ok=True, message='', item=strategy)
                
                return result
            
            result = OperationResult(ok=False, message='El item ya esta cargado en la BD', item=None)
            return result
    
    def get_all(self):
        with self.crud.get_database() as db:
            
            try:
                all_strategies = self.crud.get_all(db)
                result = OperationResult(ok=True, message='', item=all_strategies)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
                       
    def delete(self, id):
        
       with self.crud.get_database() as db:
            
            try:
                strategy = self.crud.delete(db, id)
                result = OperationResult(ok=True, message='', item=strategy)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
       
    def get_by_id(self, id):
        with self.crud.get_database() as db:
            
            try:
                strategy = self.crud.get_by_id(db, id)
                result = OperationResult(ok=True, message='', item=strategy)
                return result
            
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
        
    def update(self, id:UUID, name:str, description:str) -> OperationResult:
        
        with self.crud.get_database() as db:
            try:
                new_strategy = Strategy(id=id, Name=name, Description=description)
                
                strategy = self.crud.update(db, new_strategy)
                
                result = OperationResult(ok=True, message='', item=strategy)
                return result
                
            except Exception as e:
                result = OperationResult(ok=False, message=e, item=None)
                return result
            
        
        
