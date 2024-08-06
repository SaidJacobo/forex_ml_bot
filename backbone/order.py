import uuid
from backbone.enums import ClosePositionType, OperationType, ActionType
from backbone.utils.general_purpose import diff_pips

class Order():
    def __init__(
            self, 
            order_type:OperationType, 
            ticker:str, 
            open_time:str, 
            open_price:str, 
            units:int,
            pip_value:float,
            id:str=None, 
            stop_loss:float=None, 
            take_profit:float=None,
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
        self.position_value = round(self.open_price * self.units, 5)
        self.comment=None
        self.pip_value = pip_value

    def update(self, sl=None, tp=None):
        if sl:
            self.stop_loss=sl
        
        if tp:
            self.take_profit=tp
            
    def close(self, close_price:float, close_time:str, comment:str) -> None:
        
        self.close_price = close_price
        self.close_time = close_time
        self.profit, self.profit_in_pips = self.get_profit(self.close_price)
        self.position_value = self.get_position_value(close_price)
        self.comment=comment
        
    def get_profit_in_pips(self, price) -> float:
        return diff_pips(self.open_price, price, pip_value=self.pip_value, absolute=False) if self.operation_type == OperationType.SELL else diff_pips(price, self.open_price, pip_value=self.pip_value, absolute=False)
    
    def get_profit(self, price) -> float:
        pips = self.get_profit_in_pips(price)
        money = round(pips * self.units * self.pip_value, 5)
        return money, pips
    
    def get_position_value(self, price) -> float:
        value = round(price * self.units, 5)
        return value
