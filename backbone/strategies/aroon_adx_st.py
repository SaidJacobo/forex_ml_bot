from collections import namedtuple
from typing import List
import pandas as pd
from backbone.enums import ActionType, ClosePositionType, OperationType
from backbone.order import Order
from backbone.strategies.strategy import Strategy
from collections import namedtuple

# Declaring namedtuple()
CloseOrderFromat = namedtuple('CloseOrderFromat', ['order', 'close_type', 'close_price'])

class AroonAdxSt():
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
            self.take_profit_in_pips = self.stop_loss_in_pips * self.risk_reward_ratio
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


        # primero se fija si hay que cerrar ordenes antes de hacer nada
        _, ops = self.close_signal(
            today=today, 
            market_data=market_data, 
            open_orders=open_orders,
            balance=balance,
            price=price
        )

        result[ActionType.CLOSE] = ops # se cierran todas las ops
        

        operation_type = self.enter_signal(
            market_data=market_data, 
            open_orders=open_orders, 
            price=price
        )
        if operation_type != None:

            units, lots, margin_required = self._calculate_units_size(
                balance, 
                open_orders, 
                price, 
            )
            
            sl = self._calculate_stop_loss(operation_type, price)
            tp = self._calculate_take_profit(operation_type, price)

            result[ActionType.OPEN] = (operation_type, units, lots, tp, sl, margin_required)

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
            
            if is_pullback and candlestick_pattern:
                return operation_type

    def calculate_operation_sides(self, prices_with_indicators):
        adx_value = 25
        aroon_value = 40

        df = prices_with_indicators.copy()

        short_signals = (
            ((df['aroon'] >= aroon_value)) &
            (df['supertrend'] == -1) &
            ((df['adx'] > adx_value)) 
            & (
                (df['engulfing'] == -100) 
                | (df['hanging_man'] == -100)
                | (df['shooting_star'] == -100)
                | (df['marubozu'] == -100)
                | (df['evening_star'] == -100)
                | (df['three_black_crows'] == -100)
            )
        )

        long_signals = (
            ((df['aroon'] <= -aroon_value)) &
            (df['supertrend'] == 1) &
            ((df['adx'] > adx_value)) 
            & (
                (df['engulfing'] == 100) 
                | (df['hammer'] == 100)
                | (df['inverted_hammer'] == 100)
                | (df['marubozu'] == 100)
                | (df['morning_star'] == 100)
                | (df['three_white_soldiers'] == 100)
            )
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
            market_data:pd.DataFrame, 
            price,
            balance,
            open_orders:List[Order]=None
        ) -> ActionType:
        
        high_price = market_data.High
        low_price = market_data.Low

        orders_to_close = []


        for open_order in open_orders:
            if open_order.operation_type == OperationType.BUY:
                if low_price <= open_order.stop_loss:
                    orders_to_close.append(
                        CloseOrderFromat(open_order, ClosePositionType.STOP_LOSS, open_order.stop_loss)
                    )
                
                if high_price >= open_order.take_profit:
                    orders_to_close.append(
                        CloseOrderFromat(open_order, ClosePositionType.TAKE_PROFIT, open_order.take_profit)
                    )

            if open_order.operation_type == OperationType.SELL:
                if high_price >= open_order.stop_loss:
                    orders_to_close.append(
                        CloseOrderFromat(open_order, ClosePositionType.STOP_LOSS, open_order.stop_loss)
                    )                    
                if low_price <= open_order.take_profit:
                    orders_to_close.append(
                        CloseOrderFromat(open_order, ClosePositionType.TAKE_PROFIT, open_order.take_profit)
                    )

        total_profit = sum(order.get_profit(price)[0] for order in open_orders)
        if total_profit >= balance * 0.03: # ADVERTENCIA parametrizar
            for open_order in open_orders:
                if not any(order.order.id == open_order.id for order in orders_to_close):
                    orders_to_close.append(
                        CloseOrderFromat(open_order, None, price)
                    )
        
        if orders_to_close:
            return ActionType.CLOSE, orders_to_close 
        
        return ActionType.WAIT , None
  

    def _calculate_units_size(self, balance, open_positions, price):
        # Ajustar el porcentaje de riesgo basado en las posiciones abiertas
        risk_percentage = (len(open_positions) - self.trades_to_increment_risk) * 1.5
        risk_percentage = 1 if risk_percentage <= 0 else risk_percentage

        # Calcular el riesgo monetario permitido basado en el balance y el porcentaje de riesgo
        risk_amount = balance * (risk_percentage / 100)

        # Calcular el valor monetario del stop loss en función de los pips
        stop_loss_value = self.stop_loss_in_pips * self.pip_value

        # Calcular unidades basadas en el riesgo permitido y el stop loss
        units = risk_amount / stop_loss_value

        # Calcular el valor total de la posición apalancada
        leveraged_units = units * self.leverage
        total_value = price * units

        # Calcular el margen requerido
        margin_required = total_value / self.leverage

        lot_size = 100000
        lots = round(units / lot_size, 2)

        return units, lots, margin_required
    
    def _calculate_stop_loss(self, operation_type, price):
        price_sl = None
        if operation_type == OperationType.BUY:
            price_sl = price - (self.stop_loss_in_pips * self.pip_value)
        
        elif operation_type == OperationType.SELL:
            price_sl = price + (self.stop_loss_in_pips * self.pip_value)
            
        return round(price_sl, 5)
    

    def _calculate_take_profit(self, operation_type, price):
        price_tp = None
        if operation_type == OperationType.BUY:
            price_tp = price + (self.take_profit_in_pips * self.pip_value)
        
        elif operation_type == OperationType.SELL:
            price_tp = price - (self.take_profit_in_pips * self.pip_value)
        return round(price_tp, 4)