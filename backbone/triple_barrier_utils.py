import pandas as pd

# Función para calcular la volatilidad diaria
def get_daily_volatility(close_prices, span=100):
    returns = close_prices.pct_change()
    volatility = returns.ewm(span=span).std()
    return volatility

def apply_triple_barrier(
    close_prices, 
    max_prices, 
    min_prices, 
    daily_volatility, 
    upper_barrier_pips, 
    lower_barrier_pips, 
    max_holding_period=50, 
    pip_size=0.0001
    ):

    barriers = []
    for index in range(len(close_prices)):
        # Convertir barreras de pips a niveles porcentuales
        upper_barrier_level = close_prices[index] * (1 + (upper_barrier_pips * pip_size))
        lower_barrier_level = close_prices[index] * (1 - (lower_barrier_pips * pip_size))
        
        # Evaluar los precios futuros dentro del período máximo de mantenimiento
        for j in range(index + 1, min(index + max_holding_period, len(close_prices))):
            if close_prices[j] >= upper_barrier_level or max_prices[j] >= upper_barrier_level:
                barriers.append((index, 1))  # Etiqueta 1 para toma de ganancias
                break
            elif close_prices[j] <= lower_barrier_level or min_prices[j] <= lower_barrier_level:
                barriers.append((index, 0))  # Etiqueta 0 para stop-loss
                break
        else:
            barriers.append((index, 2))  # Etiqueta 2 si no se alcanza ninguna barrera
    
    # Revisar los eventos etiquetados como 1 para determinar si son ganancias o pérdidas
    for idx, (event_index, label) in enumerate(barriers):
        if label == 2:
            # Determinar si el precio final fue una ganancia o una pérdida
            final_price = close_prices[min(event_index + max_holding_period, len(close_prices) - 1)]
            initial_price = close_prices[event_index]
            
            if final_price >= initial_price:
                barriers[idx] = (event_index, 1)  # Etiqueta 1 para toma de ganancias
            elif final_price < initial_price:
                barriers[idx] = (event_index, 0)  # Etiqueta 0 para stop-loss

    return barriers

def triple_barrier_labeling(
        close_prices, 
        max_prices, 
        min_prices,  
        upper_barrier_pips, 
        lower_barrier_pips, 
        max_holding_period=50, 
        span=100, 
        pip_size=0.0001
    ):

    daily_volatility = get_daily_volatility(close_prices, span=span)
    
    labels = apply_triple_barrier(
        close_prices,
        max_prices,
        min_prices,
        daily_volatility, 
        upper_barrier_pips, 
        lower_barrier_pips, 
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