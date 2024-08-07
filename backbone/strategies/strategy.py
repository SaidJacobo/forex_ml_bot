from abc import ABC, abstractmethod
from collections import namedtuple
from typing import List

import pandas as pd

from backbone.enums import ActionType, OperationType
from backbone.order import Order

Result = namedtuple('Result', ['action','operation_type','order_id','comment'])

class Strategy(ABC):
    def __init__(self) -> None:
        pass


    @abstractmethod
    def enter_signal(self, market_data:pd.DataFrame, open_orders:List[Order]=None) -> OperationType:
        pass

    
    @abstractmethod
    def order_management(self, today, market_data:pd.DataFrame, open_orders:List[Order]) -> Result:
        pass


    @abstractmethod
    def close_signal(
            self, 
            today, 
            take_profit_in_money, 
            stop_loss_in_money, 
            market_data:pd.DataFrame, 
            open_orders:List[Order]=None
        ) -> ActionType:
        pass

    @abstractmethod
    def set_take_profit(self, market_data:pd.DataFrame):
        pass
    
    @abstractmethod
    def set_stop_loss(self, market_data:pd.DataFrame):
        pass