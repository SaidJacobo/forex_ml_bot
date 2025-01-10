from backbone.database.crud import CRUDBase
from backbone.entities.bot import Bot
from backbone.services.operation_result import OperationResult
bot_crud = CRUDBase(Bot)

def create_bot(
    strategy_name:str,
    metatrader_name:str,
    ticker:str,
    timeframe:str,
    risk:float,
) -> OperationResult:
    bot_data = {
        "strategy_name": strategy_name,
        "metatrader_name": metatrader_name,
        "ticker": ticker,
        "timeframe": timeframe,
        "risk": risk,
    }

    with bot_crud.get_database() as db:
        
        bot_by_filter = bot_crud.get_by_filter(db, strategy_name="botardo")
        
        if bot_by_filter is None:
            bot = bot_crud.create(db, bot_data)

            result = OperationResult(ok=True, message='', item=bot)
            
            return result
        
        result = OperationResult(ok=False, message='El item ya esta cargado en la BD', item=None)
        return result
