from importlib import import_module
import itertools

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


def calculate_units_size(account_size, risk_percentage, stop_loss_pips, pip_value):
    account_currency_risk = account_size * (risk_percentage / 100)
    units = round(account_currency_risk / (pip_value * stop_loss_pips))
    
    return units

def diff_pips(price1, price2, pip_value, absolute=True):
    if absolute:
        difference = abs(price1 - price2)
    else:
        difference = price1 - price2
    pips = difference / pip_value
    
    return pips
