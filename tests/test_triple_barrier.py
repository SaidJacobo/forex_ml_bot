import pandas as pd
import pytest
import os
import sys
import pytest

from backbone.utils.triple_barrier import apply_triple_barrier

# Cambia el directorio de trabajo al directorio raíz del proyecto
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(root_dir)
sys.path.insert(0, os.path.join(root_dir, 'src'))

@pytest.mark.parametrize(
    "close_prices, max_prices, min_prices, take_profit_in_pips, stop_loss_in_pips, side, max_holding_period, pip_size, expected",
    [
        # Casos de prueba basados en los valores proporcionados en el ejemplo
        (
            pd.Series([1.0, 1.1, 1.2, 1.3, 1.4]), 
            pd.Series([1.05, 1.15, 1.25, 1.35, 1.45]), 
            pd.Series([0.95, 1.05, 1.15, 1.25, 1.35]), 
            10, 10, 
            pd.Series([1, 1, 1, 1, 1]), 
            5, 
            0.0001, 
            [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1)]
        ),
        (
            pd.Series([1.0, 0.9, 0.8, 0.7, 0.6]), 
            pd.Series([1.05, 0.95, 0.85, 0.75, 0.65]), 
            pd.Series([0.95, 0.85, 0.75, 0.65, 0.55]), 
            10, 10, 
            pd.Series([-1, -1, -1, -1, -1]), 
            5, 
            0.0001, 
            [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1)]
        ),
        (
            pd.Series([1.0, 1.05, 1.1, 1.15, 1.2]), 
            pd.Series([1.1, 1.1, 1.2, 1.2, 1.25]), 
            pd.Series([0.95, 1.0, 1.05, 1.1, 1.15]), 
            10, 10, 
            pd.Series([1, -1, 1, -1, 1]), 
            5, 
            0.0001, 
            [(0, 1), (1,0), (2, 1), (3, 0), (4, 1)]
        ),
    ]
)
def test_apply_triple_barrier(close_prices, max_prices, min_prices, take_profit_in_pips, stop_loss_in_pips, side, max_holding_period, pip_size, expected):
    result = apply_triple_barrier(close_prices, max_prices, min_prices, take_profit_in_pips, stop_loss_in_pips, side, max_holding_period, pip_size)
    assert result == expected