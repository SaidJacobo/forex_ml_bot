from backtesting import Backtest
import pandas as pd
import plotly.express as px


def plot_stats(data, stats, strategy, plot=False):
    equity_curve = stats._equity_curve
    aligned_data = data.reindex(equity_curve.index)
    bt = Backtest(aligned_data, strategy, cash=15_000, commission=0.002)
    print(stats)
    if plot:
        bt.plot(results=stats, resample=False)


def plot_full_equity_curve(data, stats_list, warmup_bars, lookback_bars, overlay_price=True):
    equity_curves = [x["_equity_curve"].iloc[warmup_bars:] for x in stats_list]

    combined = pd.Series(dtype=float)
    for curve in equity_curves:
        # normalized_curve = curve["Equity"] / curve["Equity"].iloc[0]  # Normaliza la curva a su valor inicial
        if combined.empty:
            combined = curve["Equity"]
        else:
            # Alinea la nueva curva con la última de la serie combinada
            # normalized_curve = normalized_curve * combined.iloc[-1]
            combined = pd.concat([combined, curve["Equity"]])

    fig = px.line(x=combined.index, y=combined)
    fig.update_traces(textposition="bottom right")
    fig.show()


def walk_forward(
        strategy,
        data_full,
        warmup_bars,
        lookback_bars=28*1440,
        validation_bars=7*1440,
        params=None,
        cash=15_000, 
        commission=0.0002,
        margin=1/30

):

    stats_master = []
    equity_final = None

    for i in range(lookback_bars, len(data_full)-validation_bars, validation_bars):

        # To do anchored walk-forward, just set the first slice here to 0
        train_data = data_full.iloc[i-lookback_bars: i]

        print(f'train from {train_data.index[0]} to {train_data.index[-1]}')

        bt_training = Backtest(
            train_data, 
            strategy, 
            cash=cash, 
            commission=commission, 
            margin=margin
        )

        stats_training = bt_training.optimize(
            **params
        )
        
        validation_data = data_full.iloc[i-warmup_bars:i+validation_bars]

        print(f'validate from {validation_data.index[0]} to {validation_data.index[-1]}')

        bt_validation = Backtest(
            validation_data, 
            strategy, 
            cash=cash if equity_final == None else equity_final, 
            commission=commission, 
            margin=margin
        )

        validation_params = {param: getattr(stats_training._strategy, param) for param in params.keys() if param != 'maximize'}

        stats_validation = bt_validation.run(
            **validation_params
        )
        
        equity_final = stats_validation['Equity Final [$]']
        print(f'equity final: {equity_final}')

        stats_master.append(stats_validation)

    return stats_master