from backbone.utils.general_purpose import transformar_a_uno
from unittest.mock import patch
from backtesting import Backtest
import pandas as pd
import plotly.express as px
from backtesting._stats import compute_stats
import numpy as np
from sklearn.linear_model import LinearRegression
import MetaTrader5 as mt5

np.seterr(divide="ignore")


def optimization_function(stats):
    equity_curve = stats._equity_curve["Equity"].values
    x = np.arange(len(equity_curve)).reshape(-1, 1)
    reg = LinearRegression().fit(x, equity_curve)
    stability_ratio = reg.score(x, equity_curve)

    return (
        (stats["Return [%]"] / (1 + (-1 * stats["Max. Drawdown [%]"])))
        * np.log(1 + stats["# Trades"])
        * stability_ratio
    )


def plot_full_equity_curve(df_equity, title):

    fig = px.line(x=df_equity.index, y=df_equity.Equity)
    fig.update_layout(title=title, xaxis_title="Date", yaxis_title="Equity")
    fig.update_traces(textposition="bottom right")
    fig.show()


def get_scaled_symbol_metadata(ticker: str, metatrader=None):

    if metatrader:
        info = metatrader.symbol_info(ticker)
    else:
        if not mt5.initialize():
            print("initialize() failed, error code =", mt5.last_error())
            quit()
        info = mt5.symbol_info(ticker)
    contract_volume = info.trade_contract_size
    minimum_lot = info.volume_min
    maximum_lot = info.volume_max
    pip_value = info.trade_tick_size
    minimum_units = contract_volume * minimum_lot
    trade_tick_value_loss = info.trade_tick_value_loss
    volume_step = info.volume_step

    minimum_fraction = transformar_a_uno(minimum_units)

    scaled_contract_volume = contract_volume / minimum_fraction

    scaled_pip_value = pip_value * minimum_fraction
    scaled_minimum_lot = minimum_lot / minimum_fraction
    scaled_maximum_lot = maximum_lot / minimum_fraction

    return (
        scaled_pip_value,
        scaled_minimum_lot,
        scaled_maximum_lot,
        scaled_contract_volume,
        minimum_fraction,
        trade_tick_value_loss,
        volume_step
    )


def run_strategy(
    strategy,
    ticker,
    interval,
    prices: pd.DataFrame,
    initial_cash: float,
    commission: float,
    margin: float,
    plot=False,
    plot_path=None,
    opt_params=None,
):

    (
        scaled_pip_value,
        scaled_minimum_lot,
        scaled_maximum_lot,
        scaled_contract_volume,
        minimum_fraction,
        trade_tick_value_loss,
    ) = get_scaled_symbol_metadata(ticker)

    scaled_prices = prices.copy()
    scaled_prices.loc[:, ["Open", "High", "Low", "Close"]] = (
        scaled_prices.loc[:, ["Open", "High", "Low", "Close"]].copy() * minimum_fraction
    )

    bt_train = Backtest(
        scaled_prices, strategy, commission=commission, cash=initial_cash, margin=margin
    )

    stats = bt_train.run(
        pip_value=scaled_pip_value,
        minimum_lot=scaled_minimum_lot,
        maximum_lot=scaled_maximum_lot,
        contract_volume=scaled_contract_volume,
        trade_tick_value_loss=trade_tick_value_loss,
        opt_params=opt_params,
    )

    if plot:
        if plot_path:
            bt_train.plot(
                filename=f"{plot_path}/{ticker}_{interval}.html", resample=False
            )
            
        else:
            bt_train.plot(filename=f"./plots/{ticker}_{interval}.html", resample=False)
    
    equity_curve = stats._equity_curve["Equity"].values
    x = np.arange(len(equity_curve)).reshape(-1, 1)
    reg = LinearRegression().fit(x, equity_curve)
    stability_ratio = reg.score(x, equity_curve)

    df_stats = pd.DataFrame(
        {
            "strategy": [strategy.__name__],
            "ticker": [ticker],
            "interval": [interval],
            "stability_ratio": [stability_ratio],
            "return": [stats["Return [%]"]],
            "final_eq": [stats["Equity Final [$]"]],
            "drawdown": [stats["Max. Drawdown [%]"]],
            "drawdown_duration": [stats["Max. Drawdown Duration"]],
            "win_rate": [stats["Win Rate [%]"]],
            "sharpe_ratio": [stats["Sharpe Ratio"]],
            "trades": [stats["# Trades"]],
            "avg_trade_percent": [stats["Avg. Trade [%]"]],
            "exposure": [stats["Exposure Time [%]"]],
            "final_equity": [stats["Equity Final [$]"]],
            "Duration": [stats["Duration"]],
        }
    )

    return df_stats, stats


def walk_forward(
    strategy,
    data_full,
    warmup_bars,
    lookback_bars=28 * 1440,
    validation_bars=7 * 1440,
    params=None,
    cash=15_000,
    commission=0.0002,
    margin=1 / 30,
    verbose=False,
):

    optimized_params_history = {}
    stats_master = []
    equity_final = None

    # Iniciar el índice en el final del primer lookback

    i = lookback_bars + warmup_bars

    while i < len(data_full):

        train_data = data_full.iloc[i - lookback_bars - warmup_bars : i]

        if verbose:
            print(f"train from {train_data.index[0]} to {train_data.index[-1]}")
        bt_training = Backtest(
            train_data, strategy, cash=cash, commission=commission, margin=margin
        )

        with patch("backtesting.backtesting._tqdm", lambda *args, **kwargs: args[0]):
            stats_training = bt_training.optimize(**params)
        remaining_bars = len(data_full) - i
        current_validation_bars = min(validation_bars, remaining_bars)

        validation_data = data_full.iloc[i - warmup_bars : i + current_validation_bars]

        validation_date = validation_data.index[warmup_bars]

        if verbose:
            print(f"validate from {validation_date} to {validation_data.index[-1]}")
        bt_validation = Backtest(
            validation_data,
            strategy,
            cash=cash if equity_final is None else equity_final,
            commission=commission,
            margin=margin,
        )

        validation_params = {
            param: getattr(stats_training._strategy, param)
            for param in params.keys()
            if param != "maximize"
        }

        optimized_params_history[validation_date] = validation_params

        if verbose:
            print(validation_params)
        stats_validation = bt_validation.run(**validation_params)

        equity_final = stats_validation["Equity Final [$]"]

        if verbose:
            print(f"equity final: {equity_final}")
            print("=" * 32)
        stats_master.append(stats_validation)

        # Mover el índice `i` al final del período de validación actual

        i += current_validation_bars
    wfo_stats = get_wfo_stats(stats_master, warmup_bars, data_full)

    return wfo_stats, optimized_params_history


def get_wfo_stats(stats, warmup_bars, ohcl_data):
    trades = pd.DataFrame(
        columns=[
            "Size",
            "EntryBar",
            "ExitBar",
            "EntryPrice",
            "ExitPrice",
            "PnL",
            "ReturnPct",
            "EntryTime",
            "ExitTime",
            "Duration",
        ]
    )
    for stat in stats:
        trades = pd.concat([trades, stat._trades])
    trades.EntryBar = trades.EntryBar.astype(int)
    trades.ExitBar = trades.ExitBar.astype(int)

    equity_curves = pd.DataFrame(columns=["Equity", "DrawdownPct", "DrawdownDuration"])
    for stat in stats:
        equity_curves = pd.concat(
            [equity_curves, stat["_equity_curve"].iloc[warmup_bars:]]
        )
    wfo_stats = compute_stats(
        trades=trades,  # broker.closed_trades,
        equity=equity_curves.Equity,
        ohlc_data=ohcl_data,
        risk_free_rate=0.0,
        strategy_instance=None,  # strategy,
    )

    wfo_stats["_equity"] = equity_curves
    wfo_stats["_trades"] = trades

    return wfo_stats


def run_wfo(
    strategy,
    ticker,
    interval,
    prices: pd.DataFrame,
    initial_cash: float,
    commission: float,
    margin: float,
    optim_func,
    params: dict,
    lookback_bars: int,
    warmup_bars: int,
    validation_bars: int,
    plot=True,
):

    (
        scaled_pip_value,
        scaled_minimum_lot,
        scaled_maximum_lot,
        scaled_contract_volume,
        minimum_fraction,
        trade_tick_value_loss,
    ) = get_scaled_symbol_metadata(ticker)

    scaled_prices = prices.copy()
    scaled_prices.loc[:, ["Open", "High", "Low", "Close"]] = (
        scaled_prices.loc[:, ["Open", "High", "Low", "Close"]].copy() * minimum_fraction
    )

    params["minimum_lot"] = [scaled_minimum_lot]
    params["maximum_lot"] = [scaled_maximum_lot]
    params["contract_volume"] = [scaled_contract_volume]
    params["pip_value"] = [scaled_pip_value]
    params["trade_tick_value_loss"] = [trade_tick_value_loss]

    params["maximize"] = optim_func

    wfo_stats, optimized_params_history = walk_forward(
        strategy,
        scaled_prices,
        lookback_bars=lookback_bars,
        validation_bars=validation_bars,
        warmup_bars=warmup_bars,
        params=params,
        commission=commission,
        margin=margin,
        cash=initial_cash,
        verbose=False,
    )

    df_equity = wfo_stats["_equity"]
    df_trades = wfo_stats["_trades"]

    if plot:
        plot_full_equity_curve(df_equity, title=f"{ticker}, {interval}")
    # Calculo el stability ratio

    x = np.arange(df_equity.shape[0]).reshape(-1, 1)
    reg = LinearRegression().fit(x, df_equity.Equity)
    stability_ratio = reg.score(x, df_equity.Equity)

    # Extraigo metricas

    df_stats = pd.DataFrame(
        {
            "strategy": [strategy.__name__],
            "ticker": [ticker],
            "interval": [interval],
            "stability_ratio": [stability_ratio],
            "return": [wfo_stats["Return [%]"]],
            "final_eq": [wfo_stats["Equity Final [$]"]],
            "drawdown": [wfo_stats["Max. Drawdown [%]"]],
            "drawdown_duration": [wfo_stats["Max. Drawdown Duration"]],
            "win_rate": [wfo_stats["Win Rate [%]"]],
            "sharpe_ratio": [wfo_stats["Sharpe Ratio"]],
            "trades": [df_trades.shape[0]],
            "avg_trade_percent": [wfo_stats["Avg. Trade [%]"]],
            "exposure": [wfo_stats["Exposure Time [%]"]],
            "final_equity": [wfo_stats["Equity Final [$]"]],
            "Duration": [wfo_stats["Duration"]],
        }
    )

    return wfo_stats, df_stats, optimized_params_history
