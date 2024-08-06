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
            trade_with:List[str],
            interval:int,
            leverage:int,
            trades_to_increment_risk:int

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
            trade_with,
            money,
            interval,
            leverage,
            trades_to_increment_risk
        )

        self.positions : List[Order] = []
        self.wallet_evolution = {}
    
    def __update_account(self, order:Order) -> None:
        # Calcular el valor total de la posición y el margen requerido
        total_value = order.open_price * order.units
        margin_required = total_value / self.leverage

        # Actualizar el balance y el equity
        self.balance += order.profit
        self.margin -= margin_required  # Devolver el margen al balance
        
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
            operation_type: OperationType, 
            ticker: str, 
            date: str, 
            price: float, 
            market_data, 
        ) -> None:
        
        units, margin_required = self._calculate_units_size(price=price, ticker=ticker)

        if self.balance < margin_required:
            print("No hay suficiente balance para abrir la posición.")
        else:
            # Restar el margen requerido del balance
            self.margin += margin_required
            self.free_margin = self.equity - self.margin

            # Crear la orden y agregarla a las posiciones abiertas
            order = Order(
                order_type=operation_type,
                ticker=ticker,
                open_time=date,
                open_price=price,
                units=units,
                stop_loss=None,  # Por ahora queda así
                take_profit=None,  # Por ahora queda así
                pip_value=self.pips_per_value[ticker]
            )
            self.positions.append(order)

            print('=' * 16, f'Se abrió una nueva posición el {date}', '=' * 16)
            print(f'Units: {units}, Margin Required: {margin_required}')
            print(f'New Balance: {self.balance}')


    def close_all_positions(
            self, 
            positions, 
            date:str, 
            price:float, 
            comment:str, 
        ) -> None:

        for position in positions:
            position.close(close_price=price, close_time=date, comment=comment)
           
            self.__update_account(position)

        self.equity = self.balance  # En un sistema más complejo, equity podría calcularse de otra manera

        print('='*16, f'se cerro una posicion el {date}', '='*16)
        self.take_profit = self._calculate_take_profit() 
        self.stop_loss = self._calculate_stop_loss()



    def close_position(self, order_id:int, date:str, price:float, comment:str) -> None:
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
