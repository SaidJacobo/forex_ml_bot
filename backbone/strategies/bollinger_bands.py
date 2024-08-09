from collections import namedtuple
from typing import List
import pandas as pd
from backbone.enums import ActionType, ClosePositionType, OperationType
from backbone.order import Order
from backbone.strategies.strategy import Strategy
from collections import namedtuple

# Declaring namedtuple()
CloseOrderFromat = namedtuple('CloseOrderFromat', ['order', 'close_type', 'close_price'])

class ConsecutiveCandlesV4():
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
            total_orders:List[Order], 
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
        open_orders = [order for order in total_orders if order.close_time is None]

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
                total_orders, 
                price, 
            )
            
            sl = self._calculate_stop_loss(operation_type, price)
            tp = self._calculate_take_profit(operation_type, price)

            result[ActionType.OPEN] = (operation_type, units, lots, tp, sl, margin_required)

        return result


    def calculate_operation_sides(self, prices_with_indicators):
        df = prices_with_indicators.copy()
        
        long_signals = (
            (df['consecutive_candles'] >= 5) 
            & (df['direction'] == 'Bearish')  
        )

        short_signals = (
            (df['consecutive_candles'] >= 5) 
            & (df['direction'] == 'Bullish')  
        )
        
        df.loc[short_signals, 'side'] = -1
        df.loc[long_signals, 'side'] = 1

        df.dropna(inplace=True)
        return df

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
                is_pullback = market_data.is_acumulation
                candlestick_pattern = (market_data['engulfing'] == 1) or (market_data['hammer'] == 100) or (market_data['inverted_hammer'] == 100) or (market_data['marubozu'] == 100) or (market_data['morning_star'] == 100) or (market_data['three_white_soldiers'] == 100)
                # consecutive_candles = market_data.consecutive_candles >= 4 and market_data.direction == 'Bearish'
            else:
                is_pullback = market_data.is_acumulation
                candlestick_pattern = (market_data['engulfing'] == -1) or (market_data['hanging_man'] == -100) or (market_data['shooting_star'] == -100) or (market_data['marubozu'] == -100) or (market_data['evening_star'] == -100) or (market_data['three_black_crows'] == -100)
                # consecutive_candles = market_data.consecutive_candles >= 4 and market_data.direction == 'Bullish'
            
            if is_pullback or candlestick_pattern:
                return operation_type
        
        return None
    
    def enter_signal(
            self, 
            market_data:pd.DataFrame, 
            price, 
            open_orders:List[Order]=None
            ) -> OperationType:
        
        if not open_orders:
            if market_data.side == 1:
                return OperationType.BUY
            
            elif market_data.side == -1:
                return OperationType.SELL
            
        else:
            operation_type = self._open_new_orders_signal(
                market_data=market_data, 
                price=price, 
                open_orders=open_orders
            )
            return operation_type
        
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
        # si hay mas de una operacion abierta se activa el grid y se empiezan a promediar los profits y las perdidas
        if len(open_orders) > 1:
            last_order = max(open_orders, key=lambda ord: ord.open_time)
            
            risk_money = balance * self.risk_percentage / 100
            take_profit_money = balance * self.risk_percentage / 100 * self.risk_reward_ratio

            total_units = sum(order.units for order in open_orders)
            weighted_open_price = sum(order.open_price * order.units for order in open_orders) / total_units
            
            if last_order.operation_type == OperationType.BUY:
                # Calcular el precio necesario para alcanzar la pérdida y ganancia deseada
                loss_needed_per_unit = risk_money / total_units
                limit_price = weighted_open_price - loss_needed_per_unit

                win_needed_per_unit = take_profit_money / total_units
                take_profit_price = weighted_open_price + win_needed_per_unit

                if low_price < limit_price:
                    for open_order in open_orders:
                        orders_to_close.append(
                            CloseOrderFromat(open_order, None, limit_price)
                        )
                if high_price > take_profit_price:
                    for open_order in open_orders:
                        orders_to_close.append(
                            CloseOrderFromat(open_order, None, take_profit_price)
                        )

            if last_order.operation_type == OperationType.SELL:
                # Calcular el precio necesario para alcanzar la pérdida y ganancia deseada
                loss_needed_per_unit = risk_money / total_units
                limit_price = weighted_open_price + loss_needed_per_unit

                win_needed_per_unit = take_profit_money / total_units
                take_profit_price = weighted_open_price - win_needed_per_unit
                
                if high_price > limit_price:
                    for open_order in open_orders:
                        orders_to_close.append(
                            CloseOrderFromat(open_order, None, limit_price)
                        )

                if low_price < take_profit_price:
                    for open_order in open_orders:
                        orders_to_close.append(
                            CloseOrderFromat(open_order, None, take_profit_price)
                        )
        
        else:
            # si hay una sola se utiliza el sl y tp de toda la vida
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
       
        if orders_to_close:
            return ActionType.CLOSE, orders_to_close 
        
        return ActionType.WAIT , None
  

    def _calculate_units_size(self, balance, total_orders, price):
        # Filtra los elementos con profit menor a cero desde el final
        loss_orders = 0
        for order in reversed(total_orders):
            profit = None

            if order.close_time:
                profit = order.profit
            else:
                profit, _ = order.get_profit(price)

            if profit < 0:
                loss_orders += 1
            else:
                break

        # Ajustar el porcentaje de riesgo basado en las posiciones abiertas
        risk_percentage = self.risk_percentage + loss_orders * 1.5        

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
            
        return round(price_tp, 5)