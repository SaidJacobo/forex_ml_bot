from backbone.enums import OperationType
from backbone.utils.general_purpose import diff_pips


def n_pips(operation_type, market_data, price, pip_value, stop_loss_in_pips):

    price_sl = None
    if operation_type == OperationType.BUY:
        price_sl = price - (stop_loss_in_pips * pip_value)
    
    elif operation_type == OperationType.SELL:
        price_sl = price + (stop_loss_in_pips * pip_value)
    
    sl_in_pips = diff_pips(price, price_sl, pip_value)

    return round(price_sl, 5), sl_in_pips



def pivot_point(operation_type, market_data, price, pip_value, stop_loss_in_pips):
    price_sl = None
    max_pips_to_sl = 20 # ADVERTENCIA parametrizar

    if operation_type == OperationType.BUY:
        
        price_sl = round(market_data.s1 - (stop_loss_in_pips * pip_value), 5)
        sl_in_pips = diff_pips(price, price_sl, pip_value)
       
        if sl_in_pips > max_pips_to_sl:
            price_sl = round(price - (max_pips_to_sl * pip_value), 5)
            sl_in_pips = diff_pips(price, price_sl, pip_value)

    
    elif operation_type == OperationType.SELL:
        price_sl = round(market_data.r1 + (stop_loss_in_pips * pip_value), 5)
        sl_in_pips = diff_pips(price, price_sl, pip_value)
        
        if sl_in_pips > max_pips_to_sl:
            price_sl = round(price + (max_pips_to_sl * pip_value), 5)
            sl_in_pips = diff_pips(price, price_sl, pip_value)

    
        
    return price_sl, sl_in_pips