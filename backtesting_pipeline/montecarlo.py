import os
import sys

current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
    
import pandas as pd
import yaml
from backbone.utils.montecarlo_utils import monte_carlo_simulation_v2


if __name__ == "__main__":

    with open("./backtesting_pipeline/configs/pipeline_configs.yml", "r") as file_name:
        configs = yaml.safe_load(file_name)
    configs = configs["montecarlo"]

    in_path = configs["in_path"]
    initial_equity = configs["initial_equity"]
    n_simulations = configs["n_simulations"]
    threshold_ruin = configs["threshold_ruin"]
    out_path = configs["out_path"]

    filter_performance = pd.read_csv(os.path.join(in_path, "filter_performance.csv"))

    # Crear una lista para almacenar los resultados de cada ticker

    data_drawdown = []
    data_return = []
    montecarlo_simulations = {}

    all_drawdowns = pd.DataFrame()
    all_returns = pd.DataFrame()

    for index, row in filter_performance.iterrows():
        ticker = row.ticker
        interval = row.interval
        try:
            trades_history = pd.read_csv(
                os.path.join(in_path, f"{ticker}_{interval}", "trades.csv")
            )

            eq_curve = pd.read_csv(
                os.path.join(in_path, f"{ticker}_{interval}", "equity.csv")
            )

            # Simulación de Montecarlo para cada ticker (datos agregados)

            mc = monte_carlo_simulation_v2(
                equity_curve=eq_curve,
                trade_history=trades_history,
                n_simulations=n_simulations,
                initial_equity=initial_equity,
                threshold_ruin=threshold_ruin,
                return_raw_curves=False,
                percentiles=[0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95],
            )

            montecarlo_simulations[f"{ticker}_{interval}"] = mc
        except Exception as e:
            print(f"hubo un problema con {ticker}_{interval}: {e}")
    dd_df = pd.DataFrame()
    returns_df = pd.DataFrame()

    for ticker, mc in montecarlo_simulations.items():
        mc = mc.rename(
            columns={
                "Drawdown (%)": f"drawdown_{ticker}",
                "Final Return (%)": f"return_{ticker}",
            }
        )

        if dd_df.empty:
            dd_df = mc[[f"drawdown_{ticker}"]]
        else:
            dd_df = pd.merge(
                dd_df, mc[[f"drawdown_{ticker}"]], left_index=True, right_index=True
            )
        if returns_df.empty:
            returns_df = mc[[f"return_{ticker}"]]
        else:
            returns_df = pd.merge(
                returns_df, mc[[f"return_{ticker}"]], left_index=True, right_index=True
            )
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    returns_df.to_csv(os.path.join(out_path, "returns.csv"))

    dd_df.to_csv(os.path.join(out_path, "drawdowns.csv"))
