from collections import namedtuple
from typing import List
import pandas as pd
from backbone.enums import ActionType, OperationType
from backbone.order import Order
from backbone.strategies.strategy import Strategy

class GridSmiAdx():
    def __init__(
            self,
            ticker, 
            pip_value:float, 
            risk_reward_ratio:int, 
            risk_percentage:int,
            stop_loss_in_pips:int,
            allowed_sessions:List[str], 
            trades_to_increment_risk:int,
            leverage:int,
            interval:int,
            threshold:float

        ):
            self.ticker = ticker
            self.pip_value = pip_value
            self.risk_reward_ratio = risk_reward_ratio
            self.risk_percentage = risk_percentage
            self.stop_loss_in_pips = stop_loss_in_pips
            self.allowed_sessions = allowed_sessions
            self.trades_to_increment_risk = trades_to_increment_risk
            self.leverage = leverage
            self.interval = interval
            self.threshold = threshold


    def order_management(
            self, 
            today, 
            market_data:pd.DataFrame, 
            open_orders:List[Order], 
            balance:int, 
            equity:int, 
            margin:int, 
            price:int
        ):
        
        result = {}
        result[ActionType.OPEN] = [] # Tipo de operacion y unidades
        result[ActionType.CLOSE] = [] # Operacion
        result[ActionType.UPDATE] = [] # Operacion


        # ADVERTENCIA cambiar esto para que ponga un sl y tp individual por operacion updateandolo cada vez que abre una nueva
        # para que la suma de todos los SL sea igual al porcentage de riesgo asumido
        actual_account_take_profit = self._calculate_take_profit(
            market_data=market_data, 
            balance=balance, 
            risk_percentage=1, # ADVERTENCIA cam3biar 
            risk_reward=self.risk_reward_ratio
        )

        actual_account_stop_loss = self._calculate_stop_loss(
            market_data=market_data, 
            balance=balance
        )

        # primero se fija si hay que cerrar ordenes antes de hacer nada
        action, ops = self.close_signal(
            today=today, 
            take_profit_in_money=actual_account_take_profit, 
            stop_loss_in_money=actual_account_stop_loss, 
            market_data=market_data, 
            open_orders=open_orders,
            price=price
        )

        result[ActionType.CLOSE] = ops # se cierran todas las ops
        

        operation_type = self.enter_signal(market_data=market_data, open_orders=open_orders, price=price)
        if operation_type != None:
            units, margin_required = self._calculate_units_size(
                price=price, 
                open_positions=open_orders, 
                balance=balance
            )
            
            tp = None # ADVERTENCIA cambiar
            sl = None # ADVERTENCIA cambiar

            result[ActionType.OPEN] = (operation_type, units, tp, sl, margin_required)

        
        return result


    def _open_new_orders_signal(self, market_data:pd.DataFrame, price, open_orders:List[Order]=None) -> OperationType:

        last_order = max(open_orders, key=lambda ord: ord.open_time)
        
        operation_type = last_order.operation_type

        in_loss = None
        if operation_type == OperationType.BUY:
            in_loss = price < last_order.open_price

        elif operation_type == OperationType.SELL:
            in_loss = price > last_order.open_price

        if in_loss:
            if operation_type==OperationType.BUY:
                is_pullback = market_data['max_min'] == -1
                candlestick_pattern = (market_data['engulfing'] == 100) or (market_data['hammer'] == 100) or (market_data['inverted_hammer'] == 100) or (market_data['marubozu'] == 100) or (market_data['morning_star'] == 100) or (market_data['three_white_soldiers'] == 100)
            
            else:
                is_pullback = market_data['max_min'] == 1
                candlestick_pattern = (market_data['engulfing'] == -100) or (market_data['hanging_man'] == -100) or (market_data['shooting_star'] == -100) or (market_data['marubozu'] == -100) or (market_data['evening_star'] == -100) or (market_data['three_black_crows'] == -100)
            
            if is_pullback or candlestick_pattern:
                return operation_type

    def calculate_operation_sides(self, prices_with_indicators):
        
        df = prices_with_indicators.copy()
        
        long_signals = (
            (df['SQZ_OFF'] == 1) 
            & (df['SQZ_OFF'].shift(1) == 1)  
            & (df['SQZ_OFF'].shift(2) == 0)  
            & (df['SQZ'] > 0)  
            & (df['SQZ'] > df['SQZ'].shift(1))  
            & (df['SQZ'].shift(1) > df['SQZ'].shift(2))  
            & (df['SQZ'].shift(2) > df['SQZ'].shift(3))  
            & (df['adx'] > 25) 
            & (df['supertrend'] == 1) 
            & (df['Close'] > df['daily_sma_26']) 
        )

        short_signals = (
            (df['SQZ_OFF'] == 1) 
            & (df['SQZ_OFF'].shift(1) == 1) 
            & (df['SQZ_OFF'].shift(2) == 0) 
            & (df['SQZ'] < 0) 
            & (df['SQZ'] < df['SQZ'].shift(1)) 
            & (df['SQZ'].shift(1) < df['SQZ'].shift(2)) 
            & (df['SQZ'].shift(2) < df['SQZ'].shift(3)) 
            & (df['adx'] > 25)
            & (df['supertrend'] == -1) 
            & (df['Close'] < df['daily_sma_26']) 

        )
        
        df.loc[short_signals, 'side'] = -1
        df.loc[long_signals, 'side'] = 1

        df.dropna(inplace=True)
        return df

    def enter_signal(self, market_data:pd.DataFrame, price, open_orders:List[Order]=None) -> OperationType:
        if not open_orders:
            if market_data.side == 1:
                return OperationType.BUY
            
            elif market_data.side == -1:
                return OperationType.SELL
            
        else:
            # Gracias a esto funciona el grid trading
            op_type = self._open_new_orders_signal(market_data=market_data, open_orders=open_orders, price=price)
            return op_type
        
        return None

        
    def close_signal(
            self, 
            today, 
            take_profit_in_money, 
            stop_loss_in_money, 
            market_data:pd.DataFrame, 
            price,
            open_orders:List[Order]=None
        ) -> ActionType:
        
        if open_orders:
            total_profit = sum(order.get_profit(price)[0] for order in open_orders)

            if total_profit >= take_profit_in_money or total_profit <= -stop_loss_in_money:


                return ActionType.CLOSE, open_orders
        
        return ActionType.WAIT , None
  

    def _calculate_units_size(self, open_positions, price, balance, get_result_in_lots=False):

            # Ajustar el porcentaje de riesgo basado en las posiciones abiertas
            risk_percentage = (len(open_positions) - self.trades_to_increment_risk) * 1.5

            risk_percentage = 1 if risk_percentage <= 0 else risk_percentage

            # Calcular unidades y valor total de la posición
            units = (balance * (risk_percentage / 100)) * self.leverage / price
            total_value = price * units

            # Calcular el margen requerido
            margin_required = total_value / self.leverage

            if get_result_in_lots:
                lot_size = 100000
                number_of_lots = round(units / lot_size, 2)
                
                return number_of_lots, margin_required

            return units, margin_required
    
    
    def _calculate_stop_loss(self, market_data, balance):
        sl = balance * (self.risk_percentage / 100)
        return sl
    

    def _calculate_take_profit(self, market_data, balance, risk_percentage, risk_reward):
        tp = balance * (risk_percentage / 100) * risk_reward
        return tp