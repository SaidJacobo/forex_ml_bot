from collections import namedtuple
from typing import List
import pandas as pd
from backbone.enums import ActionType, OperationType
from backbone.order import Order
from backbone.strategies import Strategy
from backbone.utils.general_purpose import diff_pips

Result = namedtuple('Result', ['action','operation_type','order_id','comment'])

class GridSmiStrategy(Strategy):
    def __init__(self):
        pass

    def _open_new_orders_signal(self, market_data:pd.DataFrame, open_orders:List[Order]=None) -> OperationType:
        close_price = market_data.Close

        last_order = max(open_orders, key=lambda ord: ord.open_time)
        
        operation_type = last_order.operation_type

        in_loss = None
        if operation_type == OperationType.BUY:
            in_loss = close_price < last_order.open_price

        elif operation_type == OperationType.SELL:
            in_loss = close_price > last_order.open_price

        if in_loss:
            if operation_type==OperationType.BUY:
                is_pullback = market_data['max_min'] == -1
                candlestick_pattern = (market_data['engulfing'] == 100) or (market_data['hammer'] == 100) or (market_data['inverted_hammer'] == 100) or (market_data['marubozu'] == 100) or (market_data['morning_star'] == 100) or (market_data['three_white_soldiers'] == 100)
            
            else:
                is_pullback = market_data['max_min'] == 1
                candlestick_pattern = (market_data['engulfing'] == -100) or (market_data['hanging_man'] == -100) or (market_data['shooting_star'] == -100) or (market_data['marubozu'] == -100) or (market_data['evening_star'] == -100) or (market_data['three_black_crows'] == -100)
            
            if is_pullback or candlestick_pattern:
                return operation_type


    def enter_signal(self, market_data:pd.DataFrame, open_orders:List[Order]=None) -> OperationType:
        if not open_orders:
            long = (
                (market_data['SQZ_OFF'] == 1) 
                & (market_data['SQZ_OFF'].shift(1) == 1)  
                & (market_data['SQZ_OFF'].shift(2) == 0)  
                & (market_data['SQZ'] > 0)  
                & (market_data['SQZ'] > market_data['SQZ'].shift(1))  
                & (market_data['SQZ'].shift(1) > market_data['SQZ'].shift(2))  
                & (market_data['SQZ'].shift(2) > market_data['SQZ'].shift(3))  
                & (market_data['adx'] > 25) 
                & (market_data['supertrend'] == 1) 
                & (market_data['Close'] > market_data['daily_sma_26']) 
            )

            short = (
                (market_data['SQZ_OFF'] == 1) 
                & (market_data['SQZ_OFF'].shift(1) == 1) 
                & (market_data['SQZ_OFF'].shift(2) == 0) 
                & (market_data['SQZ'] < 0) 
                & (market_data['SQZ'] < market_data['SQZ'].shift(1)) 
                & (market_data['SQZ'].shift(1) < market_data['SQZ'].shift(2)) 
                & (market_data['SQZ'].shift(2) < market_data['SQZ'].shift(3)) 
                & (market_data['adx'] > 25)
                & (market_data['supertrend'] == -1) 
                & (market_data['Close'] < market_data['daily_sma_26']) 

            )

            if long:
                return OperationType.BUY
            
            if short:
                return OperationType.SELL
            
            
        else:
            op_type = self._open_new_orders_signal(market_data=market_data, open_orders=open_orders)
            return op_type
        
        return None

        
    def close_signal(
            self, 
            today, 
            take_profit_in_money, 
            stop_loss_in_money, 
            market_data:pd.DataFrame, 
            open_orders:List[Order]=None
        ) -> ActionType:
        
        if open_orders:
            close_price = market_data.Close
            total_profit = sum(order.get_profit(close_price)[0] for order in open_orders)

            if total_profit >= take_profit_in_money or total_profit <= -stop_loss_in_money:
                return ActionType.CLOSE_ALL,
        
        return None 
    
    
    def order_management(self, today, market_data:pd.DataFrame, open_orders:List[Order]) -> Result:
        
        # primero se fija si hay que cerrar ordenes antes de hacer nada
        action = self.close_signal(
            today=today, 
            take_profit_in_money=1, 
            stop_loss_in_money=1, 
            market_data=market_data, 
            open_orders=open_orders
        )

        if action != None:
            return Result(
                action, 
                None, 
                None, 
                ''
            )
        
        # Si no cerro nada, despues se fija si tiene que abrir,
        signal = self.enter_signal(market_data=market_data, open_orders=open_orders)
        if signal != None:
            return Result(
                ActionType.OPEN, 
                signal, 
                None, 
                ''
            )
        
        # Sino espera
        return Result(
            ActionType.WAIT, 
            None, 
            None, 
            ''
        )
    


    def set_take_profit(self, market_data:pd.DataFrame):
        pass
    
    def set_stop_loss(self, market_data:pd.DataFrame):
        pass


   