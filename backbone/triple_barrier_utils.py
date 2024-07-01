import numpy as np
import pandas as pd
from tqdm import tqdm

def apply_cusum_filter(raw_price, threshold):
    """
    :param raw_price: (series) of close prices.
    :param threshold: (float) when the abs(change) is larger than the threshold, the
    function captures it as an event.
    :return: (datetime index vector) vector of datetimes when the events occurred. This is used later to sample.
    """
    print('Applying Symmetric CUSUM filter.')

    t_events = []
    s_pos = 0
    s_neg = 0

    # log returns
    diff = np.log(raw_price).diff().dropna()

    # Get event time stamps for the entire series
    for i in tqdm(diff.index[1:]):
        pos = float(s_pos + diff.loc[i])
        neg = float(s_neg + diff.loc[i])
        s_pos = max(0.0, pos)
        s_neg = min(0.0, neg)

        if s_neg < -threshold:
            s_neg = 0
            t_events.append(i)

        elif s_pos > threshold:
            s_pos = 0
            t_events.append(i)

    event_timestamps = pd.DatetimeIndex(t_events)
    return event_timestamps

# Función para calcular la volatilidad diaria
def get_daily_volatility(close_prices, span=100):
    returns = close_prices.pct_change()
    volatility = returns.ewm(span=span).std()
    return volatility

def apply_triple_barrier(
    close_prices, 
    max_prices, 
    min_prices, 
    take_profit_in_pips, 
    stop_loss_in_pips, 
    side,
    max_holding_period=50, 
    pip_size=0.0001
    ):

    barriers = []
    for index in range(len(close_prices)):
        actual_close_price = close_prices[index]
        
        if side[index] == 1:
            # Para una señal de compra
            upper_barrier_level = round(actual_close_price + (take_profit_in_pips * pip_size), 4)
            lower_barrier_level = round(actual_close_price - (stop_loss_in_pips * pip_size), 4)
        elif side[index] == -1:
            # Para una señal de venta
            upper_barrier_level = round(actual_close_price + (stop_loss_in_pips * pip_size), 4)
            lower_barrier_level = round(actual_close_price - (take_profit_in_pips * pip_size), 4)
        else:
            # Si no hay señal, saltar al siguiente índice
            continue
        
        # Evaluar los precios futuros dentro del período máximo de mantenimiento
        for j in range(index + 1, min(index + max_holding_period, len(close_prices))):
            future_close_price = close_prices[j]
            future_max_price = max_prices[j]
            future_min_price = min_prices[j]
            if side[index] == 1:
                # Señal de compra: tomar ganancias si se alcanza la barrera superior
                if future_close_price >= upper_barrier_level or future_max_price >= upper_barrier_level:
                    barriers.append((index, 1))  # Etiqueta 1 para toma de ganancias
                    break
                elif future_close_price <= lower_barrier_level or future_min_price <= lower_barrier_level:
                    barriers.append((index, 0))  # Etiqueta 0 para stop-loss
                    break
            elif side[index] == -1:
                # Señal de venta: tomar ganancias si se alcanza la barrera inferior
                if future_close_price <= lower_barrier_level or future_min_price <= lower_barrier_level:
                    barriers.append((index, 1))  # Etiqueta 1 para toma de ganancias
                    break
                elif future_close_price >= upper_barrier_level or future_max_price >= upper_barrier_level:
                    barriers.append((index, 0))  # Etiqueta 0 para stop-loss
                    break
        else:
            barriers.append((index, 2))  # Etiqueta 2 si no se alcanza ninguna barrera
    
    # Revisar los eventos etiquetados como 2 para determinar si son ganancias o pérdidas
    for idx, (event_index, label) in enumerate(barriers):
        if label == 2:
            # Determinar si el precio final fue una ganancia o una pérdida
            final_price = close_prices[min(event_index + max_holding_period, len(close_prices) - 1)]
            initial_price = close_prices[event_index]
            
            if side[event_index] == 1:
                # Para una señal de compra
                if final_price >= initial_price:
                    barriers[idx] = (event_index, 1)  # Etiqueta 1 para toma de ganancias
                elif final_price < initial_price:
                    barriers[idx] = (event_index, 0)  # Etiqueta 0 para stop-loss
            elif side[event_index] == -1:
                # Para una señal de venta
                if final_price <= initial_price:
                    barriers[idx] = (event_index, 1)  # Etiqueta 1 para toma de ganancias
                elif final_price > initial_price:
                    barriers[idx] = (event_index, 0)  # Etiqueta 0 para stop-loss

    return barriers



def triple_barrier_labeling(
        close_prices, 
        max_prices, 
        min_prices,  
        take_profit_in_pips, 
        stop_loss_in_pips, 
        side,
        max_holding_period=50, 
        pip_size=0.0001,
    ):

    labels = apply_triple_barrier(
        close_prices,
        max_prices,
        min_prices,
        take_profit_in_pips, 
        stop_loss_in_pips, 
        side,
        max_holding_period, 
        pip_size
    )
    
    target = [label for _, label in labels]
    return target

def bbands(close_prices, window, no_of_stdev):
    rolling_mean = close_prices.ewm(span=window).mean()
    rolling_std = close_prices.ewm(span=window).std()

    upper_band = rolling_mean + (rolling_std * no_of_stdev)
    lower_band = rolling_mean - (rolling_std * no_of_stdev)

    return rolling_mean, upper_band, lower_band