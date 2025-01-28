import os
import sys
import yaml

current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pandas as pd
import pandas_ta as pandas_ta
import MetaTrader5 as mt5
import pandas as pd
from backtest.get_data import get_data
import pytz
from datetime import datetime

if __name__ == '__main__':
    
    with open("./backtesting_pipeline/configs/backtest_params.yml", "r") as file_name:
        bt_params = yaml.safe_load(file_name)
    
    config_path = bt_params['config_path']
    
    with open(config_path, "r") as file_name:
        configs = yaml.safe_load(file_name)

    configs = configs['get_data']
    
    out_path = configs['out_path']
    date_from = configs['date_from']
    date_to = configs['date_to']

    data_path = os.path.join(out_path, 'data')
    commissions_path = os.path.join(out_path, 'commissions')
    
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    if not os.path.exists(commissions_path):
        os.makedirs(commissions_path)

    timezone = pytz.timezone("Etc/UTC")
    date_from_get_data = datetime.strptime(date_from, "%Y-%m-%d")
    date_to_get_data = datetime.strptime(date_to, "%Y-%m-%d")

    timezone = pytz.timezone('UTC')
    date_from_get_data = timezone.localize(date_from_get_data)
    date_to_get_data = timezone.localize(date_to_get_data)


    if not mt5.initialize():
        print("initialize() failed, error code =",mt5.last_error())
        quit()

    symbols = mt5.symbols_get()

    tickers = [symbol.path.split('\\')[1] for symbol in symbols if (
        ('Agriculture' in symbol.path)
        or ('Cash CFD' in symbol.path)
        or ('Cash II CFD' in symbol.path)
        or ('Crypto CFD' in symbol.path)
        or ('Equities I CFD' in symbol.path)
        or ('Equities II CFD' in symbol.path)
        or ('Commodities' in symbol.path)
        or ('Forex' in symbol.path)
        or ('Exotics' in symbol.path)
        or ('Metals CFD' in symbol.path)
        )
    ]

    intervals = [
        mt5.TIMEFRAME_H4,
        mt5.TIMEFRAME_H3,
        mt5.TIMEFRAME_H2,
        mt5.TIMEFRAME_H1,
    ]

    symbols = get_data(tickers, intervals, date_from_get_data, date_to_get_data, save_in=data_path)

    commissions = {}

    for ticker in tickers:
        symbol_info = mt5.symbol_info_tick(ticker)
        
        avg_price = (symbol_info.bid + symbol_info.ask) / 2
        spread = symbol_info.ask - symbol_info.bid
        
        commissions[ticker] = round(spread / avg_price, 5)
        
    with open(f"{commissions_path}/commissions.yml", "w") as file:
        yaml.dump(commissions, file, default_flow_style=False)


