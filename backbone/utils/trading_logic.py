from collections import namedtuple
import random
import numpy as np
import pandas as pd
from backbone.order import Order
from backbone.enums import ClosePositionType, OperationType, ActionType

Result = namedtuple('Result', ['action','operation_type','order_id','comment'])

def find_open_order(open_orders):
    """Encuentra la orden abierta más reciente."""
    return open_orders.pop() if open_orders else None

def operation_management_logic(
        open_order:Order, 
        today:str, 
        allowed_days_in_position:int,
        use_trailing_stop:bool,
        only_indicator_close_buy_condition:bool,
        close_price:float,
        high_price:float,
        low_price:float,
        only_indicator_close_sell_condition:bool,
        model_with_indicator_open_buy_condition:bool,
        only_indicator_open_buy_condition:bool,
        model_with_indicator_open_sell_condition:bool,
        only_indicator_open_sell_condition:bool
    ) -> Result:
    
    if open_order:

        days_in_position = (today - open_order.open_time).total_seconds() // 3600
        
        if open_order.operation_type == OperationType.BUY:

            if low_price <= open_order.stop_loss:
                return Result(
                    ActionType.CLOSE, 
                    OperationType.SELL, 
                    open_order.id, 
                    ClosePositionType.STOP_LOSS
                )
            
            if high_price >= open_order.take_profit:
                return Result(
                    ActionType.CLOSE, 
                    OperationType.SELL, 
                    open_order.id, 
                    ClosePositionType.TAKE_PROFIT
                )

            if allowed_days_in_position and days_in_position >= allowed_days_in_position:
                return Result(
                    ActionType.CLOSE, 
                    OperationType.SELL, 
                    open_order.id, 
                    ClosePositionType.DAYS
                )

            # Si estás en posición pero no han pasado los días permitidos, espera
        elif open_order.operation_type == OperationType.SELL: 

            if high_price >= open_order.stop_loss:
                return Result(
                    ActionType.CLOSE, 
                    OperationType.SELL, 
                    open_order.id, 
                    ClosePositionType.STOP_LOSS
                )
            
            if low_price <= open_order.take_profit:
                return Result(
                    ActionType.CLOSE, 
                    OperationType.SELL, 
                    open_order.id, 
                    ClosePositionType.TAKE_PROFIT
                )

            if allowed_days_in_position and days_in_position >= allowed_days_in_position:
                return Result(
                    ActionType.CLOSE, 
                    OperationType.BUY, 
                    open_order.id, 
                    ClosePositionType.DAYS
                )


        if allowed_days_in_position and days_in_position < allowed_days_in_position:
            if use_trailing_stop:
                return Result(
                    ActionType.UPDATE, 
                    None, 
                    open_order.id, 
                    ClosePositionType.STOP_LOSS
                )
            else:
                return Result(
                    ActionType.WAIT, 
                    None, 
                    None, 
                    None
                )

    # Si la predicción del mercado supera el umbral superior, compra
    elif model_with_indicator_open_buy_condition or only_indicator_open_buy_condition:
        return Result(
            ActionType.OPEN, 
            OperationType.BUY,
             None, 
             ''
        )
    
    elif model_with_indicator_open_sell_condition or only_indicator_open_sell_condition:
        return Result(
            ActionType.OPEN, 
            OperationType.SELL,
             None, 
             ''
        )
    
    return Result(
        ActionType.WAIT, 
        None, 
        None, 
        ''
    )

def ml_strategy(
    today,
    actual_market_data: pd.DataFrame,
    orders: list,
    allowed_days_in_position: int,
    use_trailing_stop: bool,
    threshold: float,
):
    
    class_ = actual_market_data["pred_label"]
    proba = actual_market_data["proba"]
    side = actual_market_data["side"]

    high_price = actual_market_data["High"]
    low_price = actual_market_data["Low"]
    close_price = actual_market_data["Close"]
    
    model_with_indicator_open_buy_condition = side == 1 and class_ == 1 and proba >= threshold
    model_with_indicator_open_sell_condition = side == -1 and class_ == 1 and proba >= threshold

    only_indicator_open_buy_condition = None
    only_indicator_close_buy_condition = None
    
    only_indicator_open_sell_condition = None
    only_indicator_close_sell_condition = None

    open_order = find_open_order(orders)

    result = operation_management_logic(
        open_order=open_order,
        today=today,
        allowed_days_in_position=allowed_days_in_position,
        use_trailing_stop=use_trailing_stop,
        only_indicator_close_buy_condition=only_indicator_close_buy_condition,
        close_price=close_price,
        high_price=high_price,
        low_price=low_price,
        only_indicator_close_sell_condition=only_indicator_close_sell_condition,
        model_with_indicator_open_buy_condition=model_with_indicator_open_buy_condition,
        only_indicator_open_buy_condition=only_indicator_open_buy_condition,
        model_with_indicator_open_sell_condition=model_with_indicator_open_sell_condition,
        only_indicator_open_sell_condition=only_indicator_open_sell_condition
    )

    return result


def only_strategy(
    today,
    actual_market_data: pd.DataFrame,
    orders: list,
    allowed_days_in_position: int,
    use_trailing_stop: bool,
    threshold: float,
):
    
    side = actual_market_data["side"]
    close_price = actual_market_data["Close"]
    high_price = actual_market_data["High"]
    low_price = actual_market_data["Low"]
    
    model_with_indicator_open_buy_condition = None
    model_with_indicator_open_sell_condition = None

    only_indicator_open_buy_condition = side == 1
    only_indicator_close_buy_condition = None
    
    only_indicator_open_sell_condition = side == -1
    only_indicator_close_sell_condition = None

    open_order = find_open_order(orders)

    result = operation_management_logic(
        open_order=open_order,
        today=today,
        allowed_days_in_position=allowed_days_in_position,
        use_trailing_stop=use_trailing_stop,
        only_indicator_close_buy_condition=only_indicator_close_buy_condition,
        close_price=close_price,
        high_price=high_price,
        low_price=low_price,
        only_indicator_close_sell_condition=only_indicator_close_sell_condition,
        model_with_indicator_open_buy_condition=model_with_indicator_open_buy_condition,
        only_indicator_open_buy_condition=only_indicator_open_buy_condition,
        model_with_indicator_open_sell_condition=model_with_indicator_open_sell_condition,
        only_indicator_open_sell_condition=only_indicator_open_sell_condition
    )

    return result