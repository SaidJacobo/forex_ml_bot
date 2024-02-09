def ml_strategy(pred, actual_market_data, days_in_position, allowed_days_in_position, threshold_up, threshold_down):
    # si estas en posicion pero no pasaron los x dias, espera
    if days_in_position > -1 and days_in_position < allowed_days_in_position:
        return 'wait'
    
    # si estas en posicion y ya pasaron los x dias, vende
    elif days_in_position > -1 and days_in_position == allowed_days_in_position:
        return 'sell'
    
    if pred >= threshold_up: 
        return 'buy'
    
    return 'wait'

def sma_ml_strategy(pred, actual_market_data, days_in_position, allowed_days_in_position, threshold_up, threshold_down):
    # si estas en posicion pero no pasaron los x dias, espera
    if days_in_position > -1 and days_in_position < allowed_days_in_position:
        return 'wait'
    
    # si estas en posicion y ya pasaron los x dias, vende
    elif days_in_position > -1 and days_in_position == allowed_days_in_position:
        return 'sell'
    
    # si no estas en posicion y se que la prediccion es mayor al threshold y la media de 12 es mayor al precio de cierre
    elif days_in_position == -1 and pred >= threshold_up and actual_market_data['Close'].iloc[0] > actual_market_data['ema_12'].iloc[0]: 
        return 'buy'

    elif days_in_position > -1 and pred < threshold_down and actual_market_data['Close'].iloc[0] < actual_market_data['ema_12'].iloc[0]:
        return 'sell'
    
    return 'wait'


def macd_ml_strategy(pred, actual_market_data, days_in_position, allowed_days_in_position, threshold_up, threshold_down):
    # si estas en posicion pero no pasaron los x dias, espera
    if days_in_position > -1 and days_in_position < allowed_days_in_position:
        return 'wait'
    
    # si estas en posicion y ya pasaron los x dias, vende
    elif days_in_position > -1 and days_in_position == allowed_days_in_position:
        return 'sell'

    # si no estas en posicion y se cumple la condicion de macd junto con la prediccion compra.
    elif pred > threshold_up and actual_market_data['macd'].iloc[0] > actual_market_data['macdsignal'].iloc[0]:
        return 'buy'

    # Si se cumple la condicion de macd para vender, vende
    elif pred < threshold_down and actual_market_data['macd'].iloc[0] < actual_market_data['macdsignal'].iloc[0]:
        if days_in_position > -1:
            return 'sell'
    
    return 'wait'