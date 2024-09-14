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
    'pegRatio',
    'ask',
    'bid',
    'forwardPE',
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
    'marketCap',
    'twoHundredDayAverage',
    'recommendationKey',
    'numberOfAnalystOpinions',
    'symbol',
]
