from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    def __init__(self) -> None:
        pass


    @abstractmethod
    def enter_signal(self, market_data:pd.DataFrame):
        pass

    
    @abstractmethod
    def order_management(self, market_data:pd.DataFrame):
        pass


    @abstractmethod
    def close_signal(self, market_data:pd.DataFrame):
        pass

    @abstractmethod
    def set_take_profit(self, market_data:pd.DataFrame):
        pass
    
    @abstractmethod
    def set_stop_loss(self, market_data:pd.DataFrame):
        pass