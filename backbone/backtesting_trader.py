from backbone.enums import OperationType
from backbone.trader import ABCTrader
import pandas as pd
from backbone.order import Order
from typing import List, Tuple


class BacktestingTrader(ABCTrader):
    
    def __init__(
            self, 
            money: float, 
            trading_strategy, 
            threshold: float, 
            allowed_days_in_position: int, 
            stop_loss_in_pips: int, 
            take_profit_in_pips: int, 
            risk_percentage: int,
            allowed_sessions:List[str],
            pips_per_value:dict,
            use_trailing_stop:bool,
            trade_with:List[str]

        ):
        
        super().__init__(
            trading_strategy, 
            threshold, 
            allowed_days_in_position, 
            stop_loss_in_pips, 
            take_profit_in_pips, 
            risk_percentage,
            allowed_sessions,
            pips_per_value,
            use_trailing_stop,
            trade_with
        )

        self.actual_money = money
        self.positions : List[Order] = []
        self.wallet_evolution = {}
    
    def __update_wallet(self, order:Order) -> None:

      self.actual_money += order.profit
      self.wallet_evolution[order.close_time] = self.actual_money

      print(f'money: {self.actual_money}')

    def get_orders(self) -> Tuple[pd.DataFrame, pd.DataFrame]:

        print('saving results')

        df_orders = pd.DataFrame([vars(order) for order in self.positions])

        df_wallet = pd.DataFrame({      
            'date': self.wallet_evolution.keys(), 
            'wallet': self.wallet_evolution.values()
        })

        return df_orders, df_wallet
    
    def open_position(self, operation_type:OperationType, ticker:str, date:str, price:float) -> None:

        units = self._calculate_units_size(
            self.actual_money, 
            self.risk_percentage,
            self.stop_loss_in_pips,
            currency_pair=ticker,
        )

        price_sl = self._calculate_stop_loss(operation_type, price, ticker)
        price_tp = self._calculate_take_profit(operation_type, price, ticker)

        order = Order(
            order_type=operation_type, 
            ticker=ticker, 
            open_time=date, 
            open_price=price,
            units=units,
            stop_loss=price_sl, 
            take_profit=price_tp
        )

        self.positions.append(order)

        print('='*16, f'se abrio una nueva posicion el {date}', '='*16)

    def close_position(self, order_id:int, date:str, price:float, comment:str) -> None:
 
        order = self.get_open_orders(ticket=order_id).pop()

        order.close(close_price=price, close_time=date, comment=comment)

        self.__update_wallet(order)

        print('='*16, f'se cerro una posicion el {date}', '='*16)

    def update_position(self, order_id, actual_price, comment):
        if self.use_trailing_stop:
            open_orders = self.get_open_orders(ticket=order_id)
            
            if not open_orders:
                raise ValueError(f"No open orders found for ticket {order_id}")
            
            order = open_orders.pop()

            new_sl = None
            if order.operation_type == OperationType.BUY and actual_price > order.last_price:
                new_sl = self._calculate_stop_loss(
                    operation_type=order.operation_type, 
                    price=actual_price, 
                    ticker=order.ticker
                )
            elif order.operation_type == OperationType.SELL and actual_price < order.last_price:
                new_sl = self._calculate_stop_loss(
                    operation_type=order.operation_type, 
                    price=actual_price, 
                    ticker=order.ticker
                )

            if new_sl is not None:
                order.update(sl=new_sl, last_price=actual_price)
                print(f"Updated order {order_id}: new SL = {new_sl}, last price = {actual_price}")
            else:
                print(f"No update needed for order {order_id}: actual price = {actual_price}, last price = {order.last_price}")


    def get_open_orders(self, ticket:int=None, symbol:str=None) -> List[Order]:
        open_orders = None

        if ticket:
            open_orders = [order for order in self.positions if order.id == ticket and order.close_time is None]
            return open_orders
        
        if symbol:
            open_orders = [order for order in self.positions if order.ticker == symbol and order.close_time is None]
            return open_orders

        open_orders = [order for order in self.positions if order.close_time is None]
        return open_orders
