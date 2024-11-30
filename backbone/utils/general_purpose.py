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


def calculate_units_size(
    account_size, 
    risk_percentage, 
    stop_loss_pips, 
    pip_value, 
    maximum_units, 
    minimum_units,
    return_lots=False,
    contract_volume=None,
    actual_price=None
    
    ):
    
    valor_pip_unidad = pip_value / actual_price
    account_currency_risk = account_size * (risk_percentage / 100)
    units = round(account_currency_risk / (valor_pip_unidad * stop_loss_pips))
    
    real_units = units * 0.01 # <-- para ver que onda

    units = minimum_units if units < minimum_units else units
    units = maximum_units if units > maximum_units else units

    if return_lots:
        lots = int((units / contract_volume) * 100) / 100
        
        real_lots = round(lots * 0.01, 2) # <-- minimum fraction
        return real_lots

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
