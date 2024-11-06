import pytest
import pandas as pd
from backbone.macd_strategy import InverseMacdTrader
from unittest.mock import MagicMock

# Fixture para crear un DataFrame de prueba con precios
@pytest.fixture
def bullish_cross_df():
    data = {
        'Close': [100, 102, 104, 103, 101, 105, 107, 106],
        'Open': [99, 101, 103, 102, 100, 104, 106, 105]
    }
    return pd.DataFrame(data)

# Fixture para crear una instancia del trader
@pytest.fixture
def trader_instance():
    creds = {
        'telegram_bot_token': 'fake_token',
        'telegram_chat_id': 'fake_chat_id',
        'server': 'fake_server',
        'account': 'fake_account',
        'pw': 'fake_pw'
    }
    trader = InverseMacdTrader('FAKE_TICKER', 1, 'H1', creds)
    # Mock MetaTrader5 connection
    trader.mt5 = MagicMock()
    trader.get_open_positions = MagicMock(return_value=[])
    trader.mt5.orders_get = MagicMock(return_value=[])
    return trader

# Test para verificar que los indicadores se calculan correctamente
def test_calculate_indicators(trader_instance, bullish_cross_df):
    indicator_params = {
        'macd_fast_period': 12,
        'macd_slow_period': 26,
        'macd_signal_period': 9,
        'rsi_period': 2,
        'sma_period': 200
    }
    df_with_indicators = trader_instance.calculate_indicators(bullish_cross_df, indicator_params=indicator_params)

    # Verificar que las columnas de indicadores están presentes en el DataFrame
    assert 'macd' in df_with_indicators.columns
    assert 'sma' in df_with_indicators.columns
    assert 'rsi' in df_with_indicators.columns


# Fixture para crear un DataFrame de prueba con precios y un cruce del MACD
@pytest.fixture
def bullish_cross_df():
    data = {
        'Close': [100, 102, 104, 103, 101, 105, 107, 106],
        'macd': [1, 0.5, 0.1, -0.1, -0.5, 0.2, 0.6, 0.8],  # Simula cruce alcista en las últimas velas
        'macdsignal': [1, 1, 1, 1, 1, 0.3, 0.7, 0.5],
        'sma': [101, 102, 103, 104, 105, 106, 107, 108],
        'rsi': [70, 65, 60, 55, 50, 45, 40, 35]
    }
    return pd.DataFrame(data)

@pytest.fixture
def bearish_cross_df():
    data = {
        'Close': [100, 102, 104, 103, 101, 105, 107, 106],
        'macd': [1, 0.5, 0.1, -0.1, -0.5, 0.2, 0.6, 0.8],  # Simula cruce alcista en las últimas velas
        'macdsignal': [1, 1, 1, 1, 1, 0.3, 0.5, 0.9],
        'sma': [101, 102, 103, 104, 105, 106, 107, 108],
        'rsi': [70, 65, 60, 55, 50, 45, 40, 35]
    }
    return pd.DataFrame(data)

# Fixture para crear una instancia del trader
@pytest.fixture
def trader_instance():
    creds = {
        'telegram_bot_token': 'fake_token',
        'telegram_chat_id': 'fake_chat_id',
        'server': 'fake_server',
        'account': 'fake_account',
        'pw': 'fake_pw'
    }
    trader = InverseMacdTrader('FAKE_TICKER', 1, 'H1', creds)
    # Mock MetaTrader5 connection and order functions
    trader.mt5 = MagicMock()
    trader.mt5.order_send = MagicMock()
    trader.get_open_positions = MagicMock(return_value=[])
    trader.mt5.orders_get = MagicMock(return_value=[])
    return trader

# Test para verificar que la estrategia realiza operaciones de compra y venta
def test_strategy_buy_sell(trader_instance, bullish_cross_df):
    strategy_params = {
        'rsi_lower_threshold': 45,
        'rsi_upper_threshold': 65
    }
    # Simular la fecha actual
    actual_date = '2024-01-01 10:00:00'

    # Ejecutamos la estrategia
    trader_instance.strategy(bullish_cross_df, actual_date, strategy_params)
    assert trader_instance.mt5.order_send.called, "No se ejecutó ninguna orden de compra o venta"
    
    trader_instance.strategy(bearish_cross_df, actual_date, strategy_params)
    assert trader_instance.mt5.order_send.called, "No se ejecutó ninguna orden de compra o venta"