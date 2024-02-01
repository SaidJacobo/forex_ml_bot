def machine_learning_strategy(pred, actual_market_data, open_position, threshold_up, threshold_down):
    if pred >= threshold_up: 
        if open_position:
            return 'wait'
        
        return 'buy'

    elif pred <= threshold_down:
        if not open_position:
            return 'wait'
        return 'sell'
    
    return 'wait'

def sma_ml_strategy(pred, actual_market_data, open_position, threshold_up, threshold_down):
    if pred >= threshold_up and actual_market_data['ema_15'].iloc[0] > actual_market_data['Close'].iloc[0]: 
        if open_position:
            return 'wait'
        
        return 'buy'

    elif pred < threshold_down and actual_market_data['ema_15'].iloc[0] < actual_market_data['Close'].iloc[0]:
        if not open_position:
            return 'wait'
        
        return 'sell'
    
    return 'wait'
