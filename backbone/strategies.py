from collections import namedtuple
import numpy as np
from backbone.order import Order

Result = namedtuple('Result', ['action','operation_type','order_id','comment'])

def find_open_order(open_orders):
    """Encuentra la orden abierta más reciente."""
    return open_orders.pop() if open_orders else None

def operation_management_logic(
        open_order:Order, 
        today:str, 
        allowed_days_in_position:int,
        only_indicator_close_buy_condition:bool,
        close_price:float,
        only_indicator_close_sell_condition:bool,
        model_with_indicator_open_buy_condition:bool,
        only_indicator_open_buy_condition:bool,
        model_with_indicator_open_sell_condition:bool,
        only_indicator_open_sell_condition:bool
    ) -> Result:
    return Result("close", "sell", None, 'bla bla bla')

    if open_order:

        days_in_position = (today - open_order.open_time).days
        
        if open_order.operation_type == 'buy':
            if allowed_days_in_position and days_in_position == allowed_days_in_position:
                return Result("close", "sell", open_order.id, 'closed for days in position')
            
            # Si estás en posición y han pasado los días permitidos, vende
            # if only_indicator_close_buy_condition:
            #     return "close", "sell", open_order, 'closed for indicator signal'

            if close_price <= open_order.stop_loss:
                return Result("close", "sell", open_order.id, 'closed for stop loss')
            
            if close_price >= open_order.take_profit:
                return Result("close", "sell", open_order.id, 'closed for take profit')

            # Si estás en posición pero no han pasado los días permitidos, espera
        elif open_order.operation_type == 'sell': 
            if allowed_days_in_position and days_in_position == allowed_days_in_position:
                return Result("close", "buy", open_order.id, 'closed for days in position')
            
            # if only_indicator_close_sell_condition:
            #     return "close", "buy", open_order, 'closed for indicator signal'
            
            if close_price >= open_order.stop_loss:
                return Result("close", "sell", open_order.id, 'closed for stop loss')
            
            if close_price <= open_order.take_profit:
                return Result("close", "sell", open_order.id, 'closed for take profit')

        if allowed_days_in_position and days_in_position < allowed_days_in_position:
            return Result("wait", None, None, '')

    # Si la predicción del mercado supera el umbral superior, compra
    elif model_with_indicator_open_buy_condition or only_indicator_open_buy_condition:
        return Result("open", "buy", None, '')
    
    elif model_with_indicator_open_sell_condition or only_indicator_open_sell_condition:
        return Result("open", "sell", None, '')
    
    return Result("wait", None, None, '')

# def ml_strategy(
#     today,
#     actual_market_data,
#     orders: list,
#     allowed_days_in_position: int,
#     threshold_up: float,
#     threshold_down: float,
# ):
#     pred = actual_market_data["pred"]
#     open_order = find_open_order(orders)

#     if open_order:
#         days_in_position = (today - open_order.open_time).days

#         # Si estás en posición pero no han pasado los días permitidos, espera

#         if days_in_position < allowed_days_in_position:
#             return "wait", None, None
#         # Si estás en posición y han pasado los días permitidos, vende

#         elif days_in_position == allowed_days_in_position:
#             return "close", "sell", open_order
#     # Si la predicción del mercado supera el umbral superior, compra

#     elif pred >= threshold_up:
#         return "open", "buy", None
#     return "wait", None, None

def ma_strategy(
    today,
    actual_market_data,
    orders: list,
    allowed_days_in_position: int,
    threshold_up: float,
    threshold_down: float,
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
    close_price = actual_market_data["Close"]

    open_order = find_open_order(orders)

    model_with_indicator_open_buy_condition = np.isfinite(pred) and pred >= threshold_up and ema_12 > ema_200
    model_with_indicator_open_sell_condition = np.isfinite(pred) and pred <= threshold_down and ema_12 < ema_200

    only_indicator_open_buy_condition = np.isnan(pred) and ema_12 > ema_200
    only_indicator_close_buy_condition = ema_12 < ema_200
    
    only_indicator_open_sell_condition = np.isnan(pred) and ema_12 < ema_200
    only_indicator_close_sell_condition = ema_12 > ema_200

    result = operation_management_logic(
        open_order=open_order,
        today=today,
        allowed_days_in_position=allowed_days_in_position,
        only_indicator_close_buy_condition=only_indicator_close_buy_condition,
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
    threshold_up: float,
    threshold_down: float,
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
    close_price = actual_market_data["Close"]
    upper_bband = actual_market_data["upper_bband"]
    lower_bband = actual_market_data["lower_bband"]
    pred = actual_market_data["pred"]
    avg_bband = (upper_bband + lower_bband) / 2

    
    model_with_indicator_open_buy_condition = np.isfinite(pred) and pred >= threshold_up and close_price < avg_bband
    model_with_indicator_open_sell_condition = np.isfinite(pred) and pred <= threshold_down and close_price > avg_bband
    
    only_indicator_open_buy_condition = np.isnan(pred) and close_price < avg_bband
    only_indicator_close_buy_condition = close_price > avg_bband
    
    only_indicator_open_sell_condition = np.isnan(pred) and close_price > avg_bband
    only_indicator_close_sell_condition = close_price < avg_bband

    open_order = find_open_order(orders)

    result = operation_management_logic(
        open_order=open_order,
        today=today,
        allowed_days_in_position=allowed_days_in_position,
        only_indicator_close_buy_condition=only_indicator_close_buy_condition,
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
    threshold_up: float,
    threshold_down: float,
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
    pred = actual_market_data["pred"]
    close_price = actual_market_data["Close"]

    model_with_indicator_open_buy_condition = np.isfinite(pred) and pred >= threshold_up and macd > macd_signal
    model_with_indicator_open_sell_condition = np.isfinite(pred) and pred <= threshold_down and macd < macd_signal
    
    only_indicator_open_buy_condition = np.isnan(pred) and macd > macd_signal
    only_indicator_close_buy_condition = macd < macd_signal

    only_indicator_open_sell_condition = np.isnan(pred) and macd < macd_signal
    only_indicator_close_sell_condition = macd > macd_signal

    open_order = find_open_order(orders)

    result = operation_management_logic(
        open_order=open_order,
        today=today,
        allowed_days_in_position=allowed_days_in_position,
        only_indicator_close_buy_condition=only_indicator_close_buy_condition,
        close_price=close_price,
        only_indicator_close_sell_condition=only_indicator_close_sell_condition,
        model_with_indicator_open_buy_condition=model_with_indicator_open_buy_condition,
        only_indicator_open_buy_condition=only_indicator_open_buy_condition,
        model_with_indicator_open_sell_condition=model_with_indicator_open_sell_condition,
        only_indicator_open_sell_condition=only_indicator_open_sell_condition
    )

    return result

