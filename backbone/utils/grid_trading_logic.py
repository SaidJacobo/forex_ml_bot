from collections import namedtuple
import random
from typing import List
import numpy as np
import pandas as pd
from backbone.order import Order
from backbone.enums import ClosePositionType, OperationType, ActionType
from backbone.utils.general_purpose import diff_pips


Result = namedtuple('Result', ['action','operation_type','order_id','comment'])

def find_open_order(open_orders):
    """Encuentra la orden abierta más reciente."""
    return open_orders.pop() if open_orders else None

def operation_management_logic(
        open_orders:List[Order], 
        today:str, 
        only_indicator_close_buy_condition:bool,
        close_price:float,
        only_indicator_close_sell_condition:bool,
        model_with_indicator_open_buy_condition:bool,
        only_indicator_open_buy_condition:bool,
        model_with_indicator_open_sell_condition:bool,
        only_indicator_open_sell_condition:bool,
        take_profit_in_money:float,
        stop_loss_in_money:float,
        market_data,
        interval:int=4,
    ) -> Result:
    
    if open_orders:


        total_profit = sum(order.get_profit(close_price)[0] for order in open_orders)

        last_order = max(open_orders, key=lambda ord: ord.open_time)
        first_order = min(open_orders, key=lambda ord: ord.open_time)
        
        hours_from_last_order = (today - last_order.open_time).total_seconds() // 3600
        
        hours_from_first_order = (today - first_order.open_time).total_seconds() // 3600
        
        operation_type = last_order.operation_type

        in_loss = None
        if operation_type == OperationType.BUY:
            in_loss = close_price < last_order.open_price

        elif operation_type == OperationType.SELL:
            in_loss = close_price > last_order.open_price

        pips = diff_pips(last_order.open_price, close_price, last_order.pip_value)


        if total_profit >= take_profit_in_money or total_profit <= -stop_loss_in_money:
            return Result(
                ActionType.CLOSE_ALL,
                None,
                None,
                ''
            )
        
        # if total_profit < 0 and operation_type == OperationType.BUY and close_price < market_data['sma_26']:
        #     return Result(
        #         ActionType.CLOSE_ALL,
        #         None,
        #         None,
        #         ''
        #     )  
        
        # if total_profit < 0 and operation_type == OperationType.SELL and market_data['sma_26'] < close_price:
        #     return Result(
        #         ActionType.CLOSE_ALL,
        #         None,
        #         None,
        #         ''
        #     )      
        
        if in_loss:
            if operation_type==OperationType.BUY:
                is_pullback = market_data['max_min'] == -1
                candlestick_pattern = (market_data['engulfing'] == 100) or (market_data['hammer'] == 100) or (market_data['inverted_hammer'] == 100) or (market_data['marubozu'] == 100) or (market_data['morning_star'] == 100) or (market_data['three_white_soldiers'] == 100)
            else:
                is_pullback = market_data['max_min'] == 1
                candlestick_pattern = (market_data['engulfing'] == -100) or (market_data['hanging_man'] == -100) or (market_data['shooting_star'] == -100) or (market_data['marubozu'] == -100) or (market_data['evening_star'] == -100) or (market_data['three_black_crows'] == -100)
            
            if is_pullback or candlestick_pattern:
                return Result(
                    ActionType.OPEN, 
                    operation_type,
                    None, 
                    ''
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
    open_orders: list,
    threshold: float,
    take_profit,
    stop_loss,
    interval
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

    result = operation_management_logic(
        open_orders=open_orders,
        today=today,
        only_indicator_close_buy_condition=only_indicator_close_buy_condition,
        close_price=close_price,
        high_price=high_price,
        low_price=low_price,
        only_indicator_close_sell_condition=only_indicator_close_sell_condition,
        model_with_indicator_open_buy_condition=model_with_indicator_open_buy_condition,
        only_indicator_open_buy_condition=only_indicator_open_buy_condition,
        model_with_indicator_open_sell_condition=model_with_indicator_open_sell_condition,
        only_indicator_open_sell_condition=only_indicator_open_sell_condition,
        take_profit_in_money=take_profit,
        stop_loss_in_money=stop_loss,
        market_data=actual_market_data,
        interval=interval
    )

    return result


def only_strategy(
    today,
    actual_market_data: pd.DataFrame,
    open_orders: list,
    threshold: float,
    take_profit,
    stop_loss,
    interval
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

    result = operation_management_logic(
        open_orders=open_orders,
        today=today,
        only_indicator_close_buy_condition=only_indicator_close_buy_condition,
        close_price=close_price,
        only_indicator_close_sell_condition=only_indicator_close_sell_condition,
        model_with_indicator_open_buy_condition=model_with_indicator_open_buy_condition,
        only_indicator_open_buy_condition=only_indicator_open_buy_condition,
        model_with_indicator_open_sell_condition=model_with_indicator_open_sell_condition,
        only_indicator_open_sell_condition=only_indicator_open_sell_condition,
        take_profit_in_money=take_profit,
        stop_loss_in_money=stop_loss,
        market_data=actual_market_data,
        interval=interval
    )

    return result