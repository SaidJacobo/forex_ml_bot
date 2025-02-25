from importlib import import_module
import itertools
import logging

logger = logging.getLogger("general_purpose")


def load_function(dotpath: str):
    """Carga una función desde un módulo."""
    module_, func = dotpath.rsplit(".", maxsplit=1)
    m = import_module(module_)
    return getattr(m, func)

screener_columns = [
    'industry',
    'sector',
    'trailingPE',
    'forwardPE',
    'pegRatio',
    'trailingPegRatio'
    'beta',
    'totalDebt',
    'quickRatio',
    'currentRatio',
    'totalRevenue',
    'debtToEquity',
    'revenuePerShare',
    'returnOnAssets',
    'returnOnEquity',
    'freeCashflow',
    'operatingCashflow',
    'earningsGrowth',
    'revenueGrowth',
    'bid',
    'ask',
    'marketCap',
    'twoHundredDayAverage',
    'recommendationKey',
    'numberOfAnalystOpinions',
    'symbol',
]


def calculate_units_size(
    account_size, 
    risk_percentage, 
    stop_loss_pips, 
    maximum_lot, 
    minimum_lot,
    return_lots=False,
    contract_volume=None,
    trade_tick_value_loss=None,
    volume_step=None,
    verbose=False
    ):
    
    account_currency_risk = account_size * (risk_percentage / 100)
    lots = account_currency_risk / (trade_tick_value_loss * stop_loss_pips)
    
    if verbose:
        logger.info(f'''
            account_currency_risk: {account_currency_risk}, 
            trade_tick_value_loss: {trade_tick_value_loss},
            stop_loss_pips: {stop_loss_pips},
            lots: {lots},
        ''')
        
    
    lots = int(lots * 100) / 100
    
    lots = max(lots, minimum_lot)
    lots = min(lots, maximum_lot)    
   
    if return_lots:
        if volume_step < 1:
            number_of_decimals = len(str(volume_step).split('.')[1])
            return round(lots, number_of_decimals)
        else:
            return float(int(lots))
    
    units = int(lots * contract_volume)

    return units


def diff_pips(price1, price2, pip_value, absolute=True):
    if absolute:
        difference = abs(price1 - price2)
    else:
        difference = price1 - price2
    pips = difference / pip_value
    
    return pips

def transformar_a_uno(numero):
    # Inicializar contador de decimales
    decimales = 0
    while numero != int(numero):
        numero *= 10
        decimales += 1

    return 1 / (10 ** decimales)
