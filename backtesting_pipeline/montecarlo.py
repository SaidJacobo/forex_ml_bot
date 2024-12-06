import os
import sys

current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
    
import pandas as pd
import yaml
from backbone.utils.montecarlo_utils import monte_carlo_simulation_v2

def replace_strategy_name(obj, name):
    if isinstance(obj, dict):
        return {k: replace_strategy_name(v, name) for k, v in obj.items()}
    elif isinstance(obj, str):
        return obj.replace("{strategy_name}", name)
    return obj

if __name__ == "__main__":

    with open("./backtesting_pipeline/configs/backtest_params.yml", "r") as file_name:
        bt_params = yaml.safe_load(file_name)
    
    initial_cash = bt_params["initial_cash"]
    config_path = bt_params['config_path']
        
    with open(config_path, "r") as file_name:
        configs = yaml.safe_load(file_name)
    
    strategy_name = bt_params["strategy_name"]
    configs = replace_strategy_name(obj=configs, name=strategy_name)
            
    configs = configs["montecarlo"]

    in_path = configs["in_path"]
    n_simulations = configs["n_simulations"]
    threshold_ruin = configs["threshold_ruin"]
    out_path = configs["out_path"]
    root_path = configs["root_path"]

    filter_performance = pd.read_csv(os.path.join(in_path, "filter_performance.csv"))
    filter_performance = filter_performance.sort_values(by='custom_metric', ascending=False).drop_duplicates(subset=['ticker'])

    # Crear una lista para almacenar los resultados de cada ticker

    data_drawdown = []
    data_return = []

    all_drawdowns = pd.DataFrame()
    all_returns = pd.DataFrame()
    
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    for index, row in filter_performance.iterrows():
        ticker = row.ticker
        interval = row.interval
        method = row.method
        
        try:
            trades_history = pd.read_csv(
                os.path.join(root_path, method, f"{ticker}_{interval}", "trades.csv")
            )

            eq_curve = pd.read_csv(
                os.path.join(root_path, method, f"{ticker}_{interval}", "equity.csv"), index_col=0
            )

            # Simulación de Montecarlo para cada ticker (datos agregados)

            mc = monte_carlo_simulation_v2(
                equity_curve=eq_curve,
                trade_history=trades_history,
                n_simulations=n_simulations,
                initial_equity=initial_cash,
                threshold_ruin=threshold_ruin,
                return_raw_curves=False,
                percentiles=[0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95],
            )

            mc = mc.round(3).reset_index().rename(
                columns={'index':'metric'}
            )
            
            mc.to_csv(os.path.join(out_path, f"{ticker}_{interval}.csv"), index=False)
            
        except Exception as e:
            
            print(f"hubo un problema con {ticker}_{interval}: {e}")
