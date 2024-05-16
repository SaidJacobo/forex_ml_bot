import pandas as pd
from backbone.order import Order
from backbone.trader import ABCTrader
import MetaTrader5 as mt5
from backbone.utils import from_mt_order_to_order, from_order_to_mt_order
from typing import List, Tuple
import os


class RealtimeTrader(ABCTrader):
    
    def __init__(
            self, 
            trading_strategy, 
            threshold_up: int, 
            threshold_down: int, 
            allowed_days_in_position: int, 
            stop_loss_in_pips: int, 
            take_profit_in_pips: int, 
            risk_percentage: int,
            save_orders_path:str
        ):

        super().__init__(
            trading_strategy, 
            threshold_up, 
            threshold_down, 
            allowed_days_in_position, 
            stop_loss_in_pips, 
            take_profit_in_pips, 
            risk_percentage
        )
        # display data on the MetaTrader 5 package
        print("MetaTrader5 package author: ", mt5.__author__)
        print("MetaTrader5 package version: ", mt5.__version__)

        # establish connection to the MetaTrader 5 terminal
        if not mt5.initialize():
            raise Exception('No se pudo inicializar mt5')
        
        self.money = mt5.account_info().balance

        self.operations_mapper = {
            'buy': mt5.ORDER_TYPE_BUY,
            'sell': mt5.ORDER_TYPE_SELL,
        }

        self.operations_oposite_mapper = {
            1: mt5.ORDER_TYPE_BUY,
            0: mt5.ORDER_TYPE_SELL,
        }

        self.save_orders_path = save_orders_path
        mt5.shutdown()
  
    def get_open_orders(self, ticket:int=None, symbol:str=None) -> List[Order]:
        if not mt5.initialize():
            raise Exception('No se pudo inicializar mt5')
        
        positions = None
        
        if ticket:
            positions = list(mt5.positions_get(ticket=ticket))

        elif symbol:
            positions = list(mt5.positions_get(symbol=symbol))

        else:
            positions = list(mt5.positions_get())

        if positions:
            positions = [from_mt_order_to_order(pos) for pos in positions]

        mt5.shutdown()

        return positions
    

    def open_position(self, operation_type:str, ticker:str, date:str, price:float) -> None:
        """Abre una nueva posición de trading.

        Args:
            type: Tipo de operación (compra/venta).
            ticker (str): Ticker financiero.
            date (datetime): Fecha de la operación.
            price (float): Precio de la operación.
        """
        if not mt5.initialize():
            raise Exception('No se pudo inicializar mt5')


        symbol_info = mt5.symbol_info(ticker)
        # point = symbol_info.point
        price = symbol_info.bid if operation_type=='buy' else symbol_info.ask

        lot = self._calculate_lot_size(
            self.money, 
            self.risk_percentage,
            self.stop_loss_in_pips,
            currency_pair=ticker,
            lot_size_standard=100000
        )

        price_sl = self._calculate_stop_loss(operation_type, price, ticker)
        price_tp = self._calculate_take_profit(operation_type, price, ticker)

        action = self.operations_mapper[operation_type]

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": ticker,
            "volume": lot,
            "type": action,
            "price": price,
            "sl": price_sl,
            "tp": price_tp,
            "comment": "python script open",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # send a trading request
        result = mt5.order_send(request)
        print(result)

        mt5.shutdown()

        try:
            with open(os.path.join(self.save_orders_path, 'orders.txt'), 'a') as file:
                file.write(f'{"="*32 + "Open position" + "="*32} \n')

                for key, value in result._asdict().items():
                    file.write(f'{key}: {value}\n')

                file.write('='*32)
        except:
            with open(os.path.join(self.save_orders_path, 'orders.txt'), 'a') as file:
                file.write(f'{"="*32 + "No se pudo guardar la operacion (open)" + "="*32} \n')


    def close_position(self, order_id:int, date:str, price:float, comment:str) -> None:
        """Cierra una posición de trading.

        Args:
            order (Order): Orden de trading.
            date (datetime): Fecha de cierre de la operación.
            price (float): Precio de cierre de la operación.
        """
        position = self.get_open_orders(ticket=order_id).pop()
        
        if not mt5.initialize():
            raise Exception('No se pudo inicializar mt5')

        position = from_order_to_mt_order(position)

        symbol = position.symbol
        
        symbol_info = mt5.symbol_info(symbol)

        lot = position.volume
        
        price = symbol_info.ask if position.type=='buy' else symbol_info.bid

        action = self.operations_oposite_mapper[position.type]

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": action,
            "price": price,
            "position":order_id,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        print(result)
        mt5.shutdown()

        try: 
            with open(os.path.join(self.save_orders_path, 'orders.txt'), 'a') as file:
                file.write(f'{"="*32 + "Close position" + "="*32} \n')

                for key, value in result._asdict().items():
                    file.write(f'{key}: {value}\n')

                file.write('='*32)
        except:
            with open(os.path.join(self.save_orders_path, 'orders.txt'), 'a') as file:
                file.write(f'{"="*32 + "No se pudo guardar la operacion (close)" + "="*32} \n')

            
