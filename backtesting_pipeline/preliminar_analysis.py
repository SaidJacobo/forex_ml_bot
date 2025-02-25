import os
import sys

current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
import numpy as np
import pandas as pd
from pandas import Timestamp
import pytz
import yaml
from app.backbone.utils.general_purpose import load_function
from app.backbone.utils.wfo_utils import run_strategy

def replace_in_document(obj, element_to_replace, element):
    if isinstance(obj, dict):
        return {k: replace_in_document(v, element_to_replace, element) for k, v in obj.items()}
    elif isinstance(obj, str):
        return obj.replace(element_to_replace, element)
    return obj

if __name__ == "__main__":

    with open("./backtesting_pipeline/configs/backtest_params.yml", "r") as file_name:
        bt_params = yaml.safe_load(file_name)
    
    initial_cash = bt_params["initial_cash"]
    config_path = bt_params['config_path']
    risk = bt_params["risk"]
        
    with open("./configs/leverages.yml", "r") as file_name:
        leverages = yaml.safe_load(file_name)

    with open(config_path, "r") as file_name:
        configs = yaml.safe_load(file_name)
    
    strategy_name = bt_params["strategy_name"]
    configs = replace_in_document(obj=configs, element_to_replace="{strategy_name}", element=strategy_name)
    configs = replace_in_document(obj=configs, element_to_replace="{risk}", element=str(risk))
     
    configs = configs["preliminar_analysis"]

    date_from = configs["date_from"]
    date_to = configs["date_to"]
    strategy = configs["strategy_path"]
    in_path = configs["in_path"]
    out_path = configs["out_path"]
    strategy_path = configs["strategy_path"]
    run_only_in = configs["run_only_in"]

    out_path = os.path.join(out_path)
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    plot_path = os.path.join(out_path, "plots")
    if not os.path.exists(plot_path):
        os.makedirs(plot_path)
        
    strategy_name = strategy_path.split(".")[-1]
    strategy = load_function(strategy_path)

    commissions_path = os.path.join(in_path, "commissions/commissions.yml")
    with open(commissions_path, "r") as file_name:
        commissions = yaml.safe_load(file_name)
        
    data_path = os.path.join(in_path, "data")
    all_files = os.listdir(data_path)

    timezone = pytz.timezone("Etc/UTC")
    limited_testing_start_date = Timestamp(date_from, tz="UTC")
    limited_testing_end_date = Timestamp(date_to, tz="UTC")

    performance = pd.DataFrame()
    trade_performances = pd.DataFrame()
    stats_per_symbol = {}
    symbols = {}

    for file_name in all_files:

        file_name_components = file_name.split("_")
        ticker = file_name_components[0]
        interval = file_name_components[1]

        if run_only_in and f'{ticker}_{interval}' not in run_only_in:
            continue

        try:
            prices = pd.read_csv(os.path.join(data_path, file_name))
            prices["Date"] = pd.to_datetime(prices["Date"])
            prices = prices.set_index("Date")

            prices = prices.loc[limited_testing_start_date:limited_testing_end_date]

            if ticker not in symbols.keys():
                symbols[ticker] = {}
            
            symbols[ticker][interval] = prices

            print(f'{ticker}_{interval}')

            commission = commissions[ticker]
            leverage = leverages[ticker]
            margin = 1 / leverage
            
            if ticker not in stats_per_symbol.keys():
                stats_per_symbol[ticker] = {}
                
            df_stats, strategy_trade_performance, stats = run_strategy(
                strategy=strategy,
                ticker=ticker,
                interval=interval,
                commission=commission,
                prices=prices,
                initial_cash=initial_cash,
                margin=margin,
                risk=risk,
                plot=False,  # enviar ruta de donde quiero que se guarde
            )

            performance = pd.concat([performance, df_stats])
            trade_performances = pd.concat([trade_performances, strategy_trade_performance])
            stats_per_symbol[ticker][interval] = stats
            
        except Exception as e:
            print(f"hubo un problema con {ticker} {interval}: {e}")

    performance.to_csv(os.path.join(out_path, "performance.csv"), index=False)

    rob_test = performance.groupby(["strategy", "ticker"]).agg(
        {
            "return/dd": ["mean", "std"],
            "stability_ratio": ["mean", "std"],
            "trades": ["mean", "std"],
        }
    )

    rob_test = rob_test[
        (rob_test[("return/dd", "mean")] >= 1) & (rob_test[("trades", "mean")] > 10)
    ]
    
    rob_test.to_csv(os.path.join(out_path, "rob_test.csv"))

    average_positive_tickers = rob_test.reset_index().ticker.tolist()

    filter_performance = performance[
        performance["ticker"].isin(average_positive_tickers)
    ]
    
    filter_performance = filter_performance.sort_values(
        by=["ticker", "interval"], ascending=[True, True]
    )[
        [
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
    ].sort_values(by='custom_metric', ascending=False).drop_duplicates(subset=['ticker'])

    filter_performance['method'] = 'preliminar_analysis'

    filter_performance.to_csv(
        os.path.join(out_path, "filter_performance.csv"), index=False
    )
    
    trade_performances = trade_performances.merge(
        filter_performance[['ticker', 'interval']],
        on=['ticker', 'interval'],
        how='inner'
    )
    
    trade_performances.to_csv(
        os.path.join(out_path, "trade_performance.csv"), index=False
    )
        
    for index, row in filter_performance.iterrows():
        ticker = row.ticker
        interval = row.interval
        
        prices = symbols[ticker][interval]
        
        commission = commissions[ticker]
        leverage = leverages[ticker]
        margin = 1 / leverage

        _, _, _ = run_strategy(
            strategy=strategy,
            ticker=ticker,
            interval=interval,
            commission=commission,
            prices=prices,
            initial_cash=initial_cash,
            margin=margin,
            risk=risk,
            plot=True,
            plot_path=plot_path,
        )

        path = os.path.join(out_path, f"{ticker}_{interval}")

        if not os.path.exists(path):
            os.makedirs(path)
            
        stats_per_symbol[ticker][interval]._trades.to_csv(
            os.path.join(path, "trades.csv"), index=False
        )
        
        stats_per_symbol[ticker][interval]._equity_curve.to_csv(
            os.path.join(path, "equity.csv"),
        )