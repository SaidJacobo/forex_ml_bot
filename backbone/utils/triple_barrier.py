import random
import numpy as np
import pandas as pd
from tqdm import tqdm
from backbone.enums import OperationType

from backbone.utils.general_purpose import diff_pips

def apply_triple_barrier(
    market_data,
    stop_loss_in_pips,
    take_profit_in_pips,
    side,
    max_holding_period=50, 
    pip_size=0.0001
    ):

    close_prices = market_data.Close
    high_prices = market_data.High
    low_prices = market_data.Low

    barriers = []
    for index in range(len(close_prices)):
        actual_close_price = close_prices[index]
        
        if side[index] == 1:
            # Para una señal de compra
            upper_barrier_level = round(actual_close_price + (take_profit_in_pips * pip_size), 5)
            lower_barrier_level = round(actual_close_price - (stop_loss_in_pips * pip_size), 5)
        elif side[index] == -1:
            # Para una señal de venta
            upper_barrier_level = round(actual_close_price + (stop_loss_in_pips * pip_size), 5)
            lower_barrier_level = round(actual_close_price - (take_profit_in_pips * pip_size), 5)

        else:
            # Si no hay señal, saltar al siguiente índice
            continue
        
        # Evaluar los precios futuros dentro del período máximo de mantenimiento
        for j in range(index + 1, min(index + max_holding_period, len(close_prices))):
            future_high_price = high_prices[j]
            future_low_price = low_prices[j]
            
            if side[index] == 1:

                if future_low_price <= lower_barrier_level:
                    barriers.append((index, 0))  # Etiqueta 0 para stop-loss
                    break

                elif future_high_price >= upper_barrier_level:
                    barriers.append((index, 1))  # Etiqueta 1 para toma de ganancias
                    break

            elif side[index] == -1:
                # Señal de venta: tomar ganancias si se alcanza la barrera inferior

                if future_high_price >= upper_barrier_level:
                    barriers.append((index, 0))  # Etiqueta 0 para stop-loss
                    break

                elif future_low_price <= lower_barrier_level:
                    barriers.append((index, 1))  # Etiqueta 1 para toma de ganancias
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

    target = [label for _, label in barriers]
    
    return target