from datetime import datetime, timedelta
import os
import sys
import pytest
from collections import namedtuple
import pytest
import pandas as pd
import numpy as np
from backbone.backtesting_trader import BacktestingTrader
from backbone.enums import ActionType, OperationType  # Ajusta esto según la estructura de tu proyecto
from backbone.order import Order
from backbone.strategies import ml_strategy

# Cambia el directorio de trabajo al directorio raíz del proyecto
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(root_dir)
sys.path.insert(0, os.path.join(root_dir, 'src'))


@pytest.fixture
def sample_data():
    """Genera un DataFrame de muestra para pruebas."""
    periods = 5000
    dates = pd.date_range(start="2023-01-01", periods=periods, freq="H")
    data = {
        "Date": dates,
        "Open": np.random.rand(len(dates)) * periods,
        "High": np.random.rand(len(dates)) * periods,
        "Low": np.random.rand(len(dates)) * periods,
        "Close": np.random.rand(len(dates)) * periods,
        "spread": np.random.rand(len(dates)) * periods,
        "real_volume": np.random.rand(len(dates)) * periods,
        "Volume": np.random.rand(len(dates)) * periods
    }
    df = pd.DataFrame(data)
    return df


pips_per_value = {
    'EURUSD': 0.0001,
    'GBPUSD': 0.0001,
    'USDJPY': 0.01,
    'USDCAD': 0.0001,
    'AUDUSD': 0.0001,
    'USDCHF': 0.0001,
}

order = Order(
    id=1, 
    open_time=(datetime.now() - timedelta(hours=1)).replace(minute=0, second=0, microsecond=0), 
    order_type=OperationType.BUY, 
    stop_loss=95, 
    take_profit=105, 
    open_price=100,
    ticker='USDJPY', 
    units=20
)

trader = BacktestingTrader(
    trading_strategy=ml_strategy,
    threshold=0.5,
    allowed_days_in_position=5,
    stop_loss_in_pips=50,
    take_profit_in_pips=100,
    risk_percentage=2,
    allowed_sessions=['EURUSD', 'GBPUSD', 'USDJPY', 'USDCAD', 'AUDUSD', 'USDCHF'],
    pips_per_value=pips_per_value,
    use_trailing_stop=True,
    trade_with=['EURUSD', 'GBPUSD', 'USDJPY', 'USDCAD', 'AUDUSD', 'USDCHF'] ,
    money=1000
)

trader.positions.append(order)

def test_calculate_indicators(sample_data):
    """Prueba que los indicadores técnicos se calculan correctamente."""
    df_with_indicators = trader.calculate_indicators(sample_data.copy())
    
    # Verifica que se añaden todas las columnas de indicadores
    expected_columns = [
        'ema_12', 'ema_26', 'ema_50', 'ema_200', 'rsi',
        'upper_bband', 'middle_bband', 'lower_bband',
        'atr', 'mfi', 'adx', 'macd', 'macdsignal', 'macdhist',
        'macdhist_yesterday', 'macd_flag', 'change_percent_ch', 'change_percent_co',
        'change_percent_cl', 'change_percent_1_day', 'change_percent_2_day',
        'change_percent_3_day', 'change_percent_h', 'change_percent_o',
        'change_percent_l', 'hour', 'day', 'three_stars', 'closing_marubozu',
        'doji', 'doji_star', 'dragon_fly', 'engulfing', 'evening_doji_star',
        'hammer', 'hanging_man', 'marubozu', 'morning_star', 'shooting_star',
        'trend', 'SMA20'
    ]
    for column in expected_columns:
        assert column in df_with_indicators.columns, f"Missing column: {column}"


def test_no_future_data_leak(sample_data):
    """Prueba que no hay filtración de datos futuros en los indicadores."""
    df = sample_data
    df_with_indicators = trader.calculate_indicators(df)

    missing_dates = df[~df['Date'].isin(df_with_indicators.Date)].Date
    first_date_df_indicators = df_with_indicators.iloc[0].Date
    missing_dates = (missing_dates >= first_date_df_indicators).any()

    assert missing_dates == False, "Future data leak detected"


@pytest.mark.parametrize("account_size, risk_percentage, stop_loss_pips, currency_pair, price, expected_units", [
    (10000, 2, 50, 'EURUSD', 1.07158, 42863),
    (5000, 1, 25, 'GBPUSD', 1.26441, 25288),
    (10000, 1, 15, 'USDJPY', 160.848, 107232),
    # Agrega más casos de prueba según sea necesario
])
def test_calculate_units_size(account_size, risk_percentage, stop_loss_pips, currency_pair, price,  expected_units):
    # Llama a la función _calculate_units_size
    units = trader._calculate_units_size(account_size, risk_percentage, stop_loss_pips, currency_pair, price)

    # Verifica que el resultado sea igual al esperado
    assert units == expected_units, f"Expected units: {expected_units}, but got: {units}"


@pytest.mark.parametrize(
    "account_size, risk_percentage, stop_loss_pips, currency_pair, lot_size_standard, price, expected_lot_size", [
        (10000, 2, 50, 'EURUSD', 100000, 1.07158, 0.43),
        (5000, 1, 25, 'GBPUSD', 100000, 1.26441, 0.25),
        (10000, 1, 15, 'USDJPY', 100000, 160.848, 1.07)
    ]
)
def test_calculate_lot_size(account_size, risk_percentage, stop_loss_pips, currency_pair, lot_size_standard, price, expected_lot_size):
    calculated_lot_size = trader._calculate_lot_size(account_size, risk_percentage, stop_loss_pips, currency_pair, lot_size_standard, price)
    assert calculated_lot_size == expected_lot_size


@pytest.mark.parametrize("operation_type, price, ticker, expected_stop_loss", [
    (OperationType.BUY, 1.2000, 'EURUSD', 1.1950),
    (OperationType.SELL, 1.2000, 'EURUSD', 1.2050),
    (OperationType.BUY, 110.00, 'USDJPY', 109.50),
    (OperationType.SELL, 110.00, 'USDJPY', 110.50),
])
def test_calculate_stop_loss(operation_type, price, ticker, expected_stop_loss):
    calculated_stop_loss = trader._calculate_stop_loss(operation_type, price, ticker)
    assert calculated_stop_loss == expected_stop_loss, f"Failed for {operation_type}, {price}, {ticker}"


@pytest.mark.parametrize(
    "operation_type, price, ticker, expected_tp", [
        (OperationType.BUY, 1.2000, 'EURUSD', 1.2100),
        (OperationType.SELL, 1.2000, 'EURUSD', 1.1900),
        (OperationType.BUY, 1.3000, 'GBPUSD', 1.3100),  
        (OperationType.SELL, 1.3000, 'GBPUSD', 1.2900),
        (OperationType.BUY, 110.00, 'USDJPY', 111.00),
        (OperationType.SELL, 110.00, 'USDJPY', 109.00)
    ]
)
def test_calculate_take_profit(operation_type, price, ticker, expected_tp):
    calculated_tp = trader._calculate_take_profit(operation_type, price, ticker)
    assert calculated_tp == expected_tp


@pytest.mark.parametrize(
    "actual_market_data, actual_date, expected_action",
    [
        ({'ticker': 'EURUSD', 'Close': 1.3, 'pred_label': 1, 'proba': 0.7, 'side': 1, 'Open': 1.28, 'High': 1.35, 'Low': 1.25}, datetime(2024, 6, 28), ActionType.OPEN),
        ({'ticker': 'USDJPY', 'Close': 0.7, 'pred_label': 1, 'proba': 0.6, 'side': -1, 'Open': 0.72, 'High': 0.75, 'Low': 0.65}, datetime(2024, 6, 28), ActionType.CLOSE),
        ({'ticker': 'EURUSD', 'Close': 1.0, 'pred_label': 0, 'proba': 0.4, 'side': 1, 'Open': 1.01, 'High': 1.02, 'Low': 0.98}, datetime(2024, 6, 28), ActionType.WAIT),
    ]
)
def test_take_operation_decision(actual_market_data, actual_date, expected_action):
    actual_market_data = pd.Series(actual_market_data)
    result = trader.take_operation_decision(actual_market_data, actual_date)
    if result:
        assert result.action == expected_action
    else:
        assert result is None