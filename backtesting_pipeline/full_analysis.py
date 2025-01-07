import os
import sys

current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backbone.utils.general_purpose import load_function
from backbone.utils.wfo_utils import optimization_function, run_strategy, run_wfo
import os
import pandas as pd
import yaml
import os
import re

def find_matching_files(directory, ticker, interval):
    pattern = rf"^{ticker}_{interval}_.+_.+\.csv$"
    all_files = os.listdir(directory)
    matching_files = [file for file in all_files if re.match(pattern, file)]

    return matching_files

def replace_in_document(obj, element_to_replace, element):
    if isinstance(obj, dict):
        return {k: replace_in_document(v, element_to_replace, element) for k, v in obj.items()}
    elif isinstance(obj, str):
        return obj.replace(element_to_replace, element)
    return obj

lookback_bars_per_interval = {
    5: 3000,
    10: 2500,
    15: 2000,
    16385: 2000,
    16386: 1800,
    16387: 1800,
    16388: 1200,
    16390: 1200,
    16392: 1200,
}

if __name__ == "__main__":
    with open("./backtesting_pipeline/configs/backtest_params.yml", "r") as file_name:
        bt_params = yaml.safe_load(file_name)

    initial_cash = bt_params["initial_cash"]
    config_path = bt_params['config_path']
    risk = bt_params["risk"]
        
    with open(config_path, "r") as file_name:
        configs = yaml.safe_load(file_name)
        
    with open("./configs/leverages.yml", "r") as file_name:
            leverages = yaml.safe_load(file_name)

    strategy_name = bt_params["strategy_name"]
    configs = replace_in_document(obj=configs, element_to_replace="{strategy_name}", element=strategy_name)
    configs = replace_in_document(obj=configs, element_to_replace="{risk}", element=str(risk))
 
    configs = configs["full_analysis"]
    date_from = configs["date_from"]
    date_to = configs["date_to"]
    strategy = configs["strategy_path"]
    in_path = configs["in_path"]
    data_path = configs["data_path"]
    out_path = configs["out_path"]
    strategy_path = configs["strategy_path"]

    if not os.path.exists(out_path):
        os.makedirs(out_path)
    
    plot_path = os.path.join(out_path, "plots")
    if not os.path.exists(plot_path):
        os.makedirs(plot_path)

    filter_performance = pd.read_csv(os.path.join(in_path, "filter_performance.csv"))

    commissions_path = os.path.join(data_path, "commissions/commissions.yml")
    with open(commissions_path, "r") as file_name:
        commissions = yaml.safe_load(file_name)
    
    strategy = load_function(strategy_path)
    validation_bars = configs["validation_bars"]
    warmup_bars = configs["warmup_bars"]
    params = configs["opt_params"]

    all_wfo_performances = pd.DataFrame()
    all_opt_params = {}

    symbols = {}

    for index, row in filter_performance.iterrows():

        try:
            ticker = row.ticker
            interval = row.interval

            path = os.path.join(data_path, "data")
            matching_file = find_matching_files(path, ticker, interval).pop()

            prices = pd.read_csv(os.path.join(path, matching_file))
            prices["Date"] = pd.to_datetime(prices["Date"])
            prices = prices.set_index("Date")

            print(ticker, interval)

            commission = commissions[ticker]
            leverage = leverages[ticker]
            margin = 1 / leverage
            
            lookback_bars = lookback_bars_per_interval[interval]

            if ticker not in symbols.keys():
                symbols[ticker] = {}
            symbols[ticker][interval] = prices

            wfo_stats, df_stats, opt_params = run_wfo(
                strategy=strategy,
                ticker=ticker,
                interval=interval,
                prices=prices,
                initial_cash=initial_cash,
                commission=commission,
                margin=margin,
                optim_func=optimization_function,
                params=params,
                lookback_bars=lookback_bars,
                warmup_bars=warmup_bars,
                validation_bars=validation_bars,
                plot=False,
                risk=risk
            )

            if ticker not in all_opt_params.keys():
                all_opt_params[ticker] = {}
            all_opt_params[ticker][interval] = opt_params

            all_wfo_performances = pd.concat([all_wfo_performances, df_stats])
        except Exception as e:
            print(f"No se pudo ejecutar para el ticker {ticker}: {e}")

    performance = pd.DataFrame()
    trade_performances = pd.DataFrame()

    wfo_stats_per_symbol = {}

    if not os.path.exists(plot_path):
        os.make_dirs(plot_path)
        
    for index, row in filter_performance.iterrows():
        try:

            ticker = row.ticker
            interval = row.interval

            commission = commissions[ticker]
            leverage = leverages[ticker]
            margin = 1 / leverage
            
            print(ticker, interval)

            params = all_opt_params[ticker][interval]
            prices = symbols[ticker][interval].iloc[lookback_bars - warmup_bars + 1 :]

            if ticker not in wfo_stats_per_symbol.keys():
                wfo_stats_per_symbol[ticker] = {}
                
            df_stats, strategy_trade_performance, wfo_stats = run_strategy(
                strategy=strategy,
                ticker=ticker,
                interval=interval,
                commission=commission,
                prices=prices,
                initial_cash=initial_cash,
                margin=margin,
                risk=risk,
                opt_params=params,
                plot=True,
                plot_path=plot_path,
            )

            wfo_stats_per_symbol[ticker][interval] = wfo_stats

            performance = pd.concat([performance, df_stats])
            trade_performances = pd.concat([trade_performances, strategy_trade_performance])
       
        except Exception as e:
            print(f"hubo un problema con {ticker} {interval}: {e}")

    performance['method'] = 'wfo'
    performance.to_csv(os.path.join(out_path, "filter_performance.csv"), index=False)
    trade_performances.to_csv(os.path.join(out_path, "trade_performances.csv"), index=False)

    for index, row in performance.iterrows():
        ticker = row.ticker
        interval = row.interval

        path = os.path.join(out_path, f"{ticker}_{interval}")

        if not os.path.exists(path):
            os.makedirs(path)
            
        wfo_stats_per_symbol[ticker][interval]._trades.to_csv(
            os.path.join(path, "trades.csv"), index=False
        )

        wfo_stats_per_symbol[ticker][interval]._equity_curve.to_csv(
            os.path.join(path, "equity.csv")
        )
