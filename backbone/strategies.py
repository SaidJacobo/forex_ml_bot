from collections import namedtuple
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
        open_price:float,
        high_price:float,
        low_price:float,
        close_price:float,
        only_indicator_close_sell_condition:bool,
        model_with_indicator_open_buy_condition:bool,
        only_indicator_open_buy_condition:bool,
        model_with_indicator_open_sell_condition:bool,
        only_indicator_open_sell_condition:bool
    ) -> Result:
    
    if open_order:

        days_in_position = (today - open_order.open_time).seconds // 3600
        
        if open_order.operation_type == OperationType.BUY:
            if allowed_days_in_position and days_in_position >= allowed_days_in_position:
                return Result(
                    ActionType.CLOSE, 
                    OperationType.SELL, 
                    open_order.id, 
                    ClosePositionType.DAYS
                )
            
            if close_price <= open_order.stop_loss or low_price <= open_order.stop_loss:
                return Result(
                    ActionType.CLOSE, 
                    OperationType.SELL, 
                    open_order.id, 
                    ClosePositionType.STOP_LOSS
                )
            
            if close_price >= open_order.take_profit or high_price >= open_order.take_profit:
                return Result(
                    ActionType.CLOSE, 
                    OperationType.SELL, 
                    open_order.id, 
                    ClosePositionType.TAKE_PROFIT
                )

            # Si estás en posición pero no han pasado los días permitidos, espera
        elif open_order.operation_type == OperationType.SELL: 
            if allowed_days_in_position and days_in_position >= allowed_days_in_position:
                return Result(
                    ActionType.CLOSE, 
                    OperationType.BUY, 
                    open_order.id, 
                    ClosePositionType.DAYS
                )
            
            # if only_indicator_close_sell_condition:
            #     return ActionType.CLOSE, OperationType.BUY, open_order, 'closed for indicator signal'
            
            if close_price >= open_order.stop_loss or high_price >= open_order.stop_loss:
                return Result(
                    ActionType.CLOSE, 
                    OperationType.SELL, 
                    open_order.id, 
                    ClosePositionType.STOP_LOSS
                )
            
            if close_price <= open_order.take_profit or low_price <= open_order.take_profit:
                return Result(
                    ActionType.CLOSE, 
                    OperationType.SELL, 
                    open_order.id, 
                    ClosePositionType.TAKE_PROFIT
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

    open_price = actual_market_data["Open"]
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
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        only_indicator_close_sell_condition=only_indicator_close_sell_condition,
        model_with_indicator_open_buy_condition=model_with_indicator_open_buy_condition,
        only_indicator_open_buy_condition=only_indicator_open_buy_condition,
        model_with_indicator_open_sell_condition=model_with_indicator_open_sell_condition,
        only_indicator_open_sell_condition=only_indicator_open_sell_condition
    )

    return result

def ma_strategy(
    today,
    actual_market_data,
    orders: list,
    allowed_days_in_position: int,
    threshold: float,
):
    """
    Comprar si la predicción del modelo indica una alta probabilidad de que el precio suba y el RSI es bajo,
    lo que sugiere que la acción está en una condición de sobreventa.
    Vender si la predicción del modelo indica una alta probabilidad de que el precio baje y el RSI es alto,
    lo que sugiere que la acción está en una condición de sobrecompra.
    Mantener en cualquier otro caso.
    """
    ema_12 = actual_market_data["ema_12"]
    ema_200 = actual_market_data["ema_200"]
    pred = actual_market_data["pred"]

    open_price = actual_market_data["Open"]
    high_price = actual_market_data["High"]
    low_price = actual_market_data["Low"]
    close_price = actual_market_data["Close"]

    open_order = find_open_order(orders)

    model_with_indicator_open_buy_condition = np.isfinite(pred) and pred >= threshold and ema_12 > ema_200
    model_with_indicator_open_sell_condition = np.isfinite(pred) and pred >= threshold and ema_12 < ema_200

    only_indicator_open_buy_condition = np.isnan(pred) and ema_12 > ema_200
    only_indicator_close_buy_condition = ema_12 < ema_200
    
    only_indicator_open_sell_condition = np.isnan(pred) and ema_12 < ema_200
    only_indicator_close_sell_condition = ema_12 > ema_200

    result = operation_management_logic(
        open_order=open_order,
        today=today,
        allowed_days_in_position=allowed_days_in_position,
        only_indicator_close_buy_condition=only_indicator_close_buy_condition,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        only_indicator_close_sell_condition=only_indicator_close_sell_condition,
        model_with_indicator_open_buy_condition=model_with_indicator_open_buy_condition,
        only_indicator_open_buy_condition=only_indicator_open_buy_condition,
        model_with_indicator_open_sell_condition=model_with_indicator_open_sell_condition,
        only_indicator_open_sell_condition=only_indicator_open_sell_condition
    )

    return result

def bband_strategy(
    today,
    actual_market_data,
    orders: list,
    allowed_days_in_position: int,
    threshold: float,
):
    '''
    Comprar si la predicción del modelo indica una alta probabilidad de que el precio suba 
    y el precio actual está cerca de la banda inferior de las Bandas de Bollinger, 
    lo que sugiere una posible reversión al alza.
    Vender si la predicción del modelo indica una alta probabilidad de que el precio baje 
    y el precio actual está cerca de la banda superior de las Bandas de Bollinger, 
    lo que sugiere una posible reversión a la baja.
    Mantener en cualquier otro caso.
    '''
    upper_bband = actual_market_data["upper_bband"]
    lower_bband = actual_market_data["lower_bband"]
    avg_bband = actual_market_data["middle_bband"]
    
    class_ = actual_market_data["pred_label"]
    proba = actual_market_data["proba"]
    

    open_price = actual_market_data["Open"]
    high_price = actual_market_data["High"]
    low_price = actual_market_data["Low"]
    close_price = actual_market_data["Close"]
    
    model_with_indicator_open_buy_condition = class_ == 2 and proba >= threshold and close_price < avg_bband
    model_with_indicator_open_sell_condition = class_ == 0 and proba >= threshold and close_price > avg_bband
    
    only_indicator_open_buy_condition = None
    only_indicator_close_buy_condition = close_price > avg_bband
    
    only_indicator_open_sell_condition = None
    only_indicator_close_sell_condition = close_price < avg_bband

    open_order = find_open_order(orders)

    result = operation_management_logic(
        open_order=open_order,
        today=today,
        allowed_days_in_position=allowed_days_in_position,
        only_indicator_close_buy_condition=only_indicator_close_buy_condition,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        only_indicator_close_sell_condition=only_indicator_close_sell_condition,
        model_with_indicator_open_buy_condition=model_with_indicator_open_buy_condition,
        only_indicator_open_buy_condition=only_indicator_open_buy_condition,
        model_with_indicator_open_sell_condition=model_with_indicator_open_sell_condition,
        only_indicator_open_sell_condition=only_indicator_open_sell_condition
    )

    return result

def macd_strategy(
    today,
    actual_market_data,
    orders: list,
    allowed_days_in_position: int,
    threshold: float,
):
    '''
    Comprar si la predicción del modelo indica una alta probabilidad de que el precio suba y hay un cruce alcista 
    entre la línea MACD y la línea de señal.
    Vender si la predicción del modelo indica una alta probabilidad de que el precio baje y hay un cruce bajista 
    entre la línea MACD y la línea de señal.
    Mantener en cualquier otro caso.
    '''
    macd_signal = actual_market_data["macdsignal"]
    macd = actual_market_data["macd"]
    class_ = actual_market_data["pred_label"]
    proba = actual_market_data["proba"]

    open_price = actual_market_data["Open"]
    high_price = actual_market_data["High"]
    low_price = actual_market_data["Low"]
    close_price = actual_market_data["Close"]

    model_with_indicator_open_buy_condition = class_ == 2 and proba >= threshold and macd > macd_signal
    model_with_indicator_open_sell_condition = class_ == 0 and proba >= threshold and macd < macd_signal
    
    only_indicator_open_buy_condition = None
    only_indicator_close_buy_condition = macd < macd_signal

    only_indicator_open_sell_condition = None
    only_indicator_close_sell_condition = macd > macd_signal

    open_order = find_open_order(orders)

    result = operation_management_logic(
        open_order=open_order,
        today=today,
        allowed_days_in_position=allowed_days_in_position,
        only_indicator_close_buy_condition=only_indicator_close_buy_condition,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        only_indicator_close_sell_condition=only_indicator_close_sell_condition,
        model_with_indicator_open_buy_condition=model_with_indicator_open_buy_condition,
        only_indicator_open_buy_condition=only_indicator_open_buy_condition,
        model_with_indicator_open_sell_condition=model_with_indicator_open_sell_condition,
        only_indicator_open_sell_condition=only_indicator_open_sell_condition
    )

    return result

