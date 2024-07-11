import uuid
from backbone.enums import ClosePositionType, OperationType, ActionType

class Order():
    def __init__(
            self, 
            order_type:OperationType, 
            ticker:str, 
            open_time:str, 
            open_price:str, 
            units:int,
            id:str=None, 
            stop_loss:float=None, 
            take_profit:float=None
        ):
        self.id = uuid.uuid1() if not id else id
        self.ticker = ticker
        self.operation_type = order_type
        self.open_time = open_time
        self.close_time = None
        self.open_price = open_price
        self.last_price = open_price
        self.close_price = None
        self.profit = None
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.units = units
        self.profit_in_pips = None
        self.comment=None

    def update(self, sl=None, tp=None, last_price=None):
        if sl:
            self.stop_loss=sl
        
        if tp:
            self.take_profit=tp
            
        if last_price:
            self.last_price=last_price


    def close(self, close_price:float, close_time:str, comment:str) -> None:
        
        if comment == ClosePositionType.STOP_LOSS or comment == ClosePositionType.STOP_LOSS_RANDOM:
            close_price = self.stop_loss
        elif comment == ClosePositionType.TAKE_PROFIT or comment == ClosePositionType.TAKE_PROFIT_RANDOM:
            close_price = self.take_profit
        elif comment == ClosePositionType.DAYS:
            pass

        self.close_price = close_price
        self.close_time = close_time
        self.profit_in_pips = self.get_profit()
        self.profit =  round(self.profit_in_pips * self.units, 4)
        self.comment=comment
        
    def get_profit(self) -> float:
        return self.open_price - self.close_price if self.operation_type == OperationType.SELL else self.close_price - self.open_price