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
            trading_strategy
        ):
        
        super().__init__(
            trading_strategy=trading_strategy,
            money=money
        )

        self.wallet_evolution = {}
    
    def __update_account(self, order:Order) -> None:
        # Calcular el valor total de la posición y el margen requerido


        # Actualizar el balance y el equity
        self.balance += order.profit
        self.margin -= order.margin_required  # Devolver el margen al balance
        
        self.free_margin = self.equity - self.margin  # Devolver el margen al balance

        self.wallet_evolution[order.close_time] = self.balance
        print(f'money: {self.balance}')

    def get_orders(self) -> Tuple[pd.DataFrame, pd.DataFrame]:

        print('saving results')

        df_orders = pd.DataFrame([vars(order) for order in self.positions])

        df_wallet = pd.DataFrame({      
            'date': self.wallet_evolution.keys(), 
            'wallet': self.wallet_evolution.values()
        })

        df_equity = pd.DataFrame({      
            'date': self.equity_history.keys(), 
            'equity': self.equity_history.values()
        }) 

        return df_orders, df_wallet, df_equity
    
    
    def open_position(
        self,
        today,
        operation_type:OperationType,
        units:int,
        lots:float,
        sl:int,
        tp:int,
        margin_required:int,
        price:float 
        ) -> None:
        
        if self.balance < margin_required:
            print("No hay suficiente balance para abrir la posición.")
        else:
            # Restar el margen requerido del balance
            self.margin += margin_required
            self.free_margin = self.equity - self.margin

            # Crear la orden y agregarla a las posiciones abiertas
            order = Order(
                order_type=operation_type,
                ticker=self.trading_strategy.ticker,
                open_time=today,
                open_price=price,
                units=units,
                stop_loss=sl,  # Por ahora queda así
                take_profit=tp,  # Por ahora queda así
                pip_value=self.trading_strategy.pip_value,
                margin_required=margin_required
            )
            self.positions.append(order)

            print('=' * 16, f'Se abrió una nueva posición el {today}', '=' * 16)
            print(f'Units: {units}, Margin Required: {margin_required}')
            print(f'New Balance: {self.balance}')


    def close_position(self, orders, date:str, price:float, comment:str) -> None:
        for order_to_close in orders:
            order = order_to_close.order

            order.close(close_price=order_to_close.close_price, close_time=date, comment=order_to_close.close_type)
            
            self.__update_account(order)

            self.equity = self.balance

        print('='*16, f'se cerro una posicion el {date}', '='*16)


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
