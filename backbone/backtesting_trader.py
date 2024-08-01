from backbone.enums import ClosePositionType, OperationType
from backbone.trader import ABCTrader
import pandas as pd
from backbone.order import Order
from typing import List, Tuple

from backbone.utils.general_purpose import diff_pips


class BacktestingTrader(ABCTrader):
    
    def __init__(
            self, 
            money: float, 
            trading_strategy, 
            stop_loss_strategy, 
            take_profit_strategy, 
            trading_logic, 
            threshold: float, 
            allowed_days_in_position: int, 
            stop_loss_in_pips: int, 
            risk_reward: int, 
            risk_percentage: int,
            allowed_sessions:List[str],
            pips_per_value:dict,
            use_trailing_stop:bool,
            trade_with:List[str]

        ):
        
        super().__init__(
            trading_strategy, 
            trading_logic, 
            stop_loss_strategy, 
            take_profit_strategy, 
            threshold, 
            allowed_days_in_position, 
            stop_loss_in_pips, 
            risk_reward, 
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
    
    def open_position(self, operation_type:OperationType, ticker:str, date:str, price:float, market_data) -> None:
        
        price_sl, sl_in_pips = self._calculate_stop_loss(operation_type, market_data, price, ticker)
        
        price_tp = self._calculate_take_profit(operation_type, price, sl_in_pips, ticker)

        units = self._calculate_units_size(
            self.actual_money, 
            self.risk_percentage,
            sl_in_pips,
            currency_pair=ticker,
        )

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
 
        order = self.get_open_orders(ticket=order_id).pop() # ADVERTENCIA deberia llegar la orden, no el id

        order.close(close_price=price, close_time=date, comment=comment)

        self.__update_wallet(order)

        print('='*16, f'se cerro una posicion el {date}', '='*16)


    def update_position(self, order_id, actual_price, comment):
        if comment == ClosePositionType.STOP_LOSS:
            self._update_stop_loss(order_id, actual_price, comment)
        
        if comment == ClosePositionType.TAKE_PROFIT:
            pass



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
