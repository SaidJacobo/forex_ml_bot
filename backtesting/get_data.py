import pandas as pd
import pandas_ta as pandas_ta
import MetaTrader5 as mt5
import itertools
import MetaTrader5 as mt5
import pandas as pd

import random
random.seed(42)

def get_data(tickers, intervals, date_from, date_to):
    parameter_combinations = list(itertools.product(
        tickers, intervals
    ))

    symbols = {}

    print("MetaTrader5 package author: ", mt5.__author__)
    print("MetaTrader5 package version: ", mt5.__version__)

    # Establecer conexión con el terminal de MetaTrader 5
    if not mt5.initialize():
        raise Exception("initialize() failed, error code =", mt5.last_error())



    for ticker, interval in parameter_combinations:
        print(ticker)
        # Obtener las tasas históricas
        rates = mt5.copy_rates_range(ticker, interval, date_from, date_to)
        
        # Crear DataFrame con las tasas
        df = pd.DataFrame(rates)
        
        # Convertir el tiempo de segundos a formato datetime
        df['time'] = pd.to_datetime(df['time'], unit='s')


        # Renombrar columnas para el ticker principal
        df = df.rename(columns={
            'time': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'tick_volume': 'Volume'
        }).set_index('Date')


        if ticker not in symbols.keys():
            symbols[ticker] = {}
            symbols[ticker][interval] = {}

        symbols[ticker][interval] = df


    # Cerrar la conexión con MetaTrader 5
    mt5.shutdown()
    
    return symbols
    