def ml_strategy(actual_market_data, days_in_position, allowed_days_in_position, threshold_up, threshold_down):
    # si estas en posicion pero no pasaron los x dias, espera
    if days_in_position > -1 and days_in_position < allowed_days_in_position:
        return 'wait'
    
    # si estas en posicion y ya pasaron los x dias, vende
    elif days_in_position > -1 and days_in_position == allowed_days_in_position:
        return 'sell'
    
    if actual_market_data['pred'] >= threshold_up: 
        return 'buy'
    
    return 'wait'

def sma_ml_strategy(actual_market_data, days_in_position, allowed_days_in_position, threshold_up, threshold_down):
    # si estas en posicion pero no pasaron los x dias, espera
    if days_in_position > -1 and days_in_position < allowed_days_in_position:
        return 'wait'
    
    # si estas en posicion y ya pasaron los x dias, vende
    elif days_in_position > -1 and days_in_position == allowed_days_in_position:
        return 'sell'
    
    # si no estas en posicion y se que la prediccion es mayor al threshold y la media de 12 es mayor al precio de cierre
    elif days_in_position == -1 and actual_market_data['pred'] >= threshold_up and actual_market_data['Close'] > actual_market_data['ema_12']: 
        return 'buy'

    elif days_in_position > -1 and actual_market_data['pred'] < threshold_down and actual_market_data['Close'] < actual_market_data['ema_12']:
        return 'sell'
    
    return 'wait'


def macd_ml_strategy(actual_market_data, days_in_position, allowed_days_in_position, threshold_up, threshold_down):
    # si estas en posicion pero no pasaron los x dias, espera
    if days_in_position > -1 and days_in_position < allowed_days_in_position:
        return 'wait'
    
    # si estas en posicion y ya pasaron los x dias, vende
    elif days_in_position > -1 and days_in_position == allowed_days_in_position:
        return 'sell'

    # si no estas en posicion y se cumple la condicion de macd junto con la prediccion compra.
    elif actual_market_data['pred'] > threshold_up and actual_market_data['macd'] > actual_market_data['macdsignal']:
        return 'buy'

    # Si se cumple la condicion de macd para vender, vende
    elif actual_market_data['pred'] < threshold_down and actual_market_data['macd'] < actual_market_data['macdsignal']:
        if days_in_position > -1:
            return 'sell'
    
    return 'wait'