import os
import re
import sys

current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
    
import numpy as np
import pandas as pd
import yaml
from backbone.utils.general_purpose import load_function
from backbone.utils.wfo_utils import run_strategy


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

time_frames = {
    16385: 1,
    16386: 2,
    16387: 3,
    16388: 4,
}

cols_to_calculate_mean = [
    'stability_ratio',
    "return",
    "drawdown",
    "return/dd",
    "custom_metric",
    'drawdown_duration', 
    'win_rate', 
    'sharpe_ratio',
    'trades', 
    'exposure', 
    'final_equity', 
    "Duration",
]

ordered_cols = [
    "strategy",
    "ticker",
    "interval",
    "stability_ratio",
    "trades",
    "return",
    "drawdown",
    "return/dd",
    "custom_metric",
    "win_rate",
    "Duration",
]

if __name__ == '__main__':
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
       
    configs = configs["random_test"]

    date_from = configs["date_from"]
    date_to = configs["date_to"]
    data_path = configs["data_path"]
    
    in_path = configs["in_path"]
    root_path = configs["root_path"]
    
    n_iterations = configs["n_iterations"]
    
    out_path = configs["out_path"]
    strategy_path = configs["strategy_path"]
    run_only_in = configs['run_only_in']
    
    plot_path = os.path.join(out_path, "plots")
    
    if not os.path.exists(out_path):
        os.makedirs(out_path)
        
    if not os.path.exists(plot_path):
        os.makedirs(plot_path)

    filter_performance = pd.read_csv(os.path.join(in_path, "filter_performance.csv"))
    
    if run_only_in:
        filter_performance['ticker_interval'] = filter_performance['ticker'] + '_' + filter_performance['interval'].astype(str)
        filter_performance = filter_performance[filter_performance['ticker_interval'].isin(run_only_in)]

    commissions_path = os.path.join(data_path, "commissions/commissions.yml")
    with open(commissions_path, "r") as file_name:
        commissions = yaml.safe_load(file_name)
    
    strategy = load_function(strategy_path)

    performance = pd.DataFrame()
    trade_performance = pd.DataFrame()
    all_opt_params = {}

    symbols = {}
    stats_per_symbol = {}

    for _, row in filter_performance.iterrows():
        try:
            ticker = row.ticker
            interval = row.interval
            method = row.method
            
            path = os.path.join(data_path, "data")
            matching_file = find_matching_files(path, ticker, interval).pop()

            # busco el df del activo
            prices = pd.read_csv(os.path.join(path, matching_file))
            prices["Date"] = pd.to_datetime(prices["Date"])
            prices = prices.set_index("Date")
            
            # busco los trades para obtener sus probs
            trade_history = pd.read_csv(
                os.path.join(root_path, method, f'{ticker}_{interval}', 'trades.csv')
            )
            
            equity_curve = pd.read_csv(
                os.path.join(root_path, method, f'{ticker}_{interval}', 'equity.csv')
            )
            
            long_trades = trade_history[trade_history['Size'] > 0]
            short_trades = trade_history[trade_history['Size'] < 0]
            
            prob_trade = len(trade_history) / len(equity_curve)  # Probabilidad de realizar un trade
            prob_long = len(long_trades) / len(trade_history) if len(trade_history) > 0 else 0
            prob_short = len(short_trades) / len(trade_history) if len(trade_history) > 0 else 0

            timeframe_hours = time_frames[interval]
            trade_history["Duration"] = pd.to_timedelta(trade_history["Duration"])
            trade_history["Bars"] = (trade_history["Duration"] / pd.Timedelta(hours=timeframe_hours)).apply(lambda x: int(round(x)))

            avg_trade_duration = trade_history.Bars.mean()
            std_trade_duration = trade_history.Bars.std()

            params = {
                'prob_trade': prob_trade,
                'prob_long': prob_long,
                'prob_short': prob_short,
                'avg_trade_duration': avg_trade_duration,
                'std_trade_duration': std_trade_duration,
            }

            print(ticker, interval)
            commission = commissions[ticker]
            leverage = leverages[ticker]
            margin = 1 / leverage
            
            if ticker not in stats_per_symbol.keys():
                stats_per_symbol[ticker] = {}
            
            mean_performance = pd.DataFrame()
            mean_trade_performance = pd.DataFrame()
            
            for i in range(0, n_iterations):
                first = i == 0
                
                df_stats, strategy_trade_performance, stats = run_strategy(
                    strategy=strategy,
                    ticker=ticker,
                    interval=interval,
                    commission=commission,
                    prices=prices,
                    initial_cash=initial_cash,
                    margin=margin,
                    risk=risk,
                    opt_params=params,
                    plot=False,
                    plot_path=plot_path,
                )

                mean_performance = pd.concat([mean_performance, df_stats])
                mean_trade_performance = pd.concat([mean_trade_performance, strategy_trade_performance])
                
                if i == 0:
                    stats_per_symbol[ticker][interval] = stats

            mean_performance = mean_performance.groupby(by=['strategy','ticker','interval'])[cols_to_calculate_mean].mean().reset_index()
            mean_trade_performance = mean_trade_performance.groupby(by=['strategy','ticker','interval']).mean().reset_index()
            
            performance = pd.concat([performance, mean_performance])
            trade_performance = pd.concat([trade_performance, mean_trade_performance])
        
        except Exception as e:
            print(f"hubo un problema con {ticker} {interval}: {e}")
    
    if performance.size > 0:
        performance = performance.sort_values(
            by=["ticker", "interval"], ascending=[True, True]
        )[ordered_cols]

    performance.to_csv(os.path.join(out_path, "random_test_mean_performance.csv"), index=False)
    trade_performance.to_csv(os.path.join(out_path, "random_test_trade_mean_performance.csv"), index=False)
    
    for index, row in filter_performance.iterrows():
        ticker = row.ticker
        interval = row.interval

        path = os.path.join(out_path, f"{ticker}_{interval}")

        if not os.path.exists(path):
            os.makedirs(path)
            
        stats_per_symbol[ticker][interval]._trades.to_csv(
            os.path.join(path, "trades.csv"), index=False
        )

        stats_per_symbol[ticker][interval]._equity_curve.to_csv(
            os.path.join(path, "equity.csv")
        )
    
    