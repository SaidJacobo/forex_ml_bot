import numpy as np


def find_open_order(orders):
    """Encuentra la orden abierta más reciente."""
    open_orders = [order for order in orders if order.close_date is None]
    return open_orders.pop() if open_orders else None


def ml_strategy(
    today,
    actual_market_data,
    orders: list,
    allowed_days_in_position: int,
    threshold_up: float,
    threshold_down: float,
):
    pred = actual_market_data["pred"]
    open_order = find_open_order(orders)

    if open_order:
        days_in_position = (today - open_order.open_date).days

        # Si estás en posición pero no han pasado los días permitidos, espera

        if days_in_position < allowed_days_in_position:
            return "wait", None, None
        # Si estás en posición y han pasado los días permitidos, vende

        elif days_in_position == allowed_days_in_position:
            return "close", "sell", open_order
    # Si la predicción del mercado supera el umbral superior, compra

    elif pred >= threshold_up:
        return "open", "buy", None
    return "wait", None, None


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

    open_order = find_open_order(orders)

    model_with_indicator_buy_condition = np.isfinite(pred) and pred >= threshold_up and ema_12 > ema_200
    only_indicator_buy_condition = np.isnan(pred) and ema_12 > ema_200

    if open_order:
        days_in_position = (today - open_order.open_date).days

        # Si estás en posición y han pasado los días permitidos, vende
        if ema_12 < ema_200 or days_in_position == allowed_days_in_position:
            return "close", "sell", open_order
        # Si estás en posición pero no han pasado los días permitidos, espera

        if days_in_position < allowed_days_in_position:
            return "wait", None, None
    # Si la predicción del mercado supera el umbral superior, compra

    elif model_with_indicator_buy_condition or only_indicator_buy_condition:
        return "open", "buy", None
    
    return "wait", None, None

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

    open_order = find_open_order(orders)
    
    model_with_indicator_buy_condition = np.isfinite(pred) and pred >= threshold_up and close_price < avg_bband
    only_indicator_buy_condition = np.isnan(pred) and close_price < avg_bband

    if open_order:
        days_in_position = (today - open_order.open_date).days
        # Si estás en posición y han pasado los días permitidos, vende
        if close_price > avg_bband or days_in_position == allowed_days_in_position:
            return "close", "sell", open_order
        # Si estás en posición pero no han pasado los días permitidos, espera

        if days_in_position < allowed_days_in_position:
            return "wait", None, None
    # Si la predicción del mercado supera el umbral superior, compra

    elif model_with_indicator_buy_condition or only_indicator_buy_condition:
        return "open", "buy", None
    
    return "wait", None, None

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

    model_with_indicator_buy_condition = np.isfinite(pred) and pred >= threshold_up and macd > macd_signal
    only_indicator_buy_condition = np.isnan(pred) and macd > macd_signal

    open_order = find_open_order(orders)
    if open_order:
        days_in_position = (today - open_order.open_date).days
        # Si estás en posición y han pasado los días permitidos, vende
        if macd < macd_signal or days_in_position == allowed_days_in_position:
            return "close", "sell", open_order
        # Si estás en posición pero no han pasado los días permitidos, espera

        if days_in_position < allowed_days_in_position:
            return "wait", None, None
    # Si la predicción del mercado supera el umbral superior, compra

    elif model_with_indicator_buy_condition or only_indicator_buy_condition:
        return "open", "buy", None
    
    return "wait", None, None
