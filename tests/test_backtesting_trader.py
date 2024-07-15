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

def test_no_future_data_leak(sample_data):
    """Prueba que no hay filtración de datos futuros en los indicadores."""
    df = sample_data
    df_with_indicators = trader.calculate_indicators(df, ticker='EURUSD')

    missing_dates = df[~df['Date'].isin(df_with_indicators.Date)].Date
    first_date_df_indicators = df_with_indicators.iloc[0].Date
    missing_dates = (missing_dates >= first_date_df_indicators).any()

    assert missing_dates == False, "Future data leak detected"


@pytest.mark.parametrize("account_size, risk_percentage, stop_loss_pips, currency_pair, expected_units", [
    (10000, 2, 50, 'EURUSD', 40000),
    (5000, 1, 25, 'GBPUSD', 20000),
    (10000, 1, 15, 'USDJPY', 667),
    # Agrega más casos de prueba según sea necesario
])
def test_calculate_units_size(account_size, risk_percentage, stop_loss_pips, currency_pair, expected_units):
    # Llama a la función _calculate_units_size
    units = trader._calculate_units_size(account_size, risk_percentage, stop_loss_pips, currency_pair)

    # Verifica que el resultado sea igual al esperado
    assert units == expected_units, f"Expected units: {expected_units}, but got: {units}"


@pytest.mark.parametrize(
    "account_size, risk_percentage, stop_loss_pips, currency_pair, lot_size_standard, price, expected_lot_size", [
        (10000, 2, 50, 'EURUSD', 100000, 1.07158, 0.4),
        (5000, 1, 25, 'GBPUSD', 100000, 1.26441, 0.2),
        (10000, 1, 15, 'USDJPY', 100000, 160.848, 0.01)
    ]
)
def test_calculate_lot_size(account_size, risk_percentage, stop_loss_pips, currency_pair, lot_size_standard, price, expected_lot_size):
    calculated_lot_size = trader._calculate_lot_size(account_size, risk_percentage, stop_loss_pips, currency_pair, lot_size_standard)
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


@pytest.mark.parametrize(
    "operation_type, ticker, date, price, expected_units, expected_stop_loss, expected_take_profit",
    [
        (OperationType.BUY, 'EURUSD', datetime(2024, 6, 28), 1.2, 40000, 1.195, 1.205),
        (OperationType.SELL, 'GBPUSD', datetime(2024, 6, 28), 1.3, 40000, 1.305, 1.295),
        (OperationType.BUY, 'USDJPY', datetime(2024, 6, 28), 110.0, 400, 109.5, 110.5),
        (OperationType.SELL, 'USDCHF', datetime(2024, 6, 28), 0.9, 40000, 0.905, 0.895),
    ]
)
def test_open_position(operation_type, ticker, date, price, expected_units, expected_stop_loss, expected_take_profit):

    # Mocking the initial parameters
    trader.actual_money = 10000
    trader.risk_percentage = 2
    trader.stop_loss_in_pips = 50
    trader.take_profit_in_pips = 50
    trader.pips_per_value = pips_per_value
    trader.positions = []

    trader.open_position(operation_type, ticker, date, price)

    assert len(trader.positions) == 1
    assert trader.positions[0].stop_loss == expected_stop_loss
    assert trader.positions[0].take_profit == expected_take_profit
    assert trader.positions[0].units == expected_units


@pytest.mark.parametrize(
    "order_id, date, price, comment, initial_positions, expected_wallet_update",
    [
        (
            1, datetime(2024, 6, 28), 1.25, "Take profit hit",
            [Order(id=1, order_type=OperationType.BUY, ticker='EURUSD', open_time=datetime(2024, 6, 27), open_price=1.2, units=1000, stop_loss=1.15, take_profit=1.25)],
            50  # assuming the profit added to the wallet is 50
        ),
        (
            2, datetime(2024, 6, 28), 1.45, "Stop loss hit",
            [Order(id=2, order_type=OperationType.SELL, ticker='GBPUSD', open_time=datetime(2024, 6, 27), open_price=1.4, units=1000, stop_loss=1.45, take_profit=1.3)],
            -50  # assuming the loss deducted from the wallet is 50
        )
    ]
)
def test_close_position(order_id, date, price, comment, initial_positions, expected_wallet_update):

    # Mocking initial positions and wallet update function
    trader.positions = initial_positions
    trader.__update_wallet = lambda order: expected_wallet_update

    trader.close_position(order_id, date, price, comment)

    assert trader.positions[0].profit == expected_wallet_update
    assert trader.positions[0].close_price == price


@pytest.mark.parametrize(
    "order_id, actual_price, comment, use_trailing_stop, initial_order, expected_order, exception_expected",
    [
        (
            1, 1.4000, "Price increased", True,
            Order(order_type=OperationType.BUY, ticker='EURUSD', open_time=datetime(2024, 6, 27), open_price=1.3, units=1000, stop_loss=1.2000, take_profit=1.4),
            Order(order_type=OperationType.BUY, ticker='EURUSD', open_time=datetime(2024, 6, 27), open_price=1.3, units=1000, stop_loss=1.3995, take_profit=1.4),
            False
        ),
        (
            2, 1.2500, "Price decreased", True,
            Order(order_type=OperationType.SELL, ticker='GBPUSD', open_time=datetime(2024, 6, 27), open_price=1.3, units=1000, stop_loss=1.35, take_profit=1.2),
            Order(order_type=OperationType.SELL, ticker='GBPUSD', open_time=datetime(2024, 6, 27), open_price=1.3, units=1000, stop_loss=1.2505, take_profit=1.2),
            False
        ),
        (
            3, 1.25, "No trailing stop", False,
            Order(order_type=OperationType.BUY, ticker='EURUSD', open_time=datetime(2024, 6, 27), open_price=1.2, units=1000, stop_loss=1.15, take_profit=1.25),
            Order(order_type=OperationType.BUY, ticker='EURUSD', open_time=datetime(2024, 6, 27), open_price=1.2, units=1000, stop_loss=1.15, take_profit=1.25),
            False
        ),
        (
            4, 1.25, "Order not found", True,
            None,
            None,
            True
        )
    ]
)
def test_update_position(order_id, actual_price, comment, use_trailing_stop, initial_order, expected_order, exception_expected):
    trader.use_trailing_stop = use_trailing_stop
    trader.stop_loss_in_pips = 5
    if initial_order:
        initial_order.id = order_id
        trader.positions = [initial_order]
    else:
        trader.positions = []

    if exception_expected:
        with pytest.raises(Exception):
            trader.update_position(order_id, actual_price, comment)
    else:
        trader.update_position(order_id, actual_price, comment)
        updated_order = trader.positions[0]
        assert updated_order.stop_loss == expected_order.stop_loss
        assert updated_order.take_profit == expected_order.take_profit


@pytest.mark.parametrize(
    "ticket, symbol, positions, expected_open_orders",
    [
        (
            1, None,
            [
                Order(order_type=OperationType.BUY, ticker='EURUSD', open_time=datetime(2024, 6, 27), open_price=1.2, units=1000, stop_loss=1.15, take_profit=1.25, id=1),
                Order(order_type=OperationType.SELL, ticker='GBPUSD', open_time=datetime(2024, 6, 28), open_price=1.3, units=1000, stop_loss=1.35, take_profit=1.2, id=2)
            ],
            [
                Order(order_type=OperationType.BUY, ticker='EURUSD', open_time=datetime(2024, 6, 27), open_price=1.2, units=1000, stop_loss=1.15, take_profit=1.25, id=1)
            ]
        ),
        (
            None, 'GBPUSD',
            [
                Order(order_type=OperationType.BUY, ticker='EURUSD', open_time=datetime(2024, 6, 27), open_price=1.2, units=1000, stop_loss=1.15, take_profit=1.25, id=3),
                Order(order_type=OperationType.SELL, ticker='GBPUSD', open_time=datetime(2024, 6, 28), open_price=1.3, units=1000, stop_loss=1.35, take_profit=1.2, id=4)
            ],
            [
                Order(order_type=OperationType.SELL, ticker='GBPUSD', open_time=datetime(2024, 6, 28), open_price=1.3, units=1000, stop_loss=1.35, take_profit=1.2, id=4)
            ]
        ),
        (
            None, None,
            [
                Order(order_type=OperationType.BUY, ticker='EURUSD', open_time=datetime(2024, 6, 27), open_price=1.2, units=1000, stop_loss=1.15, take_profit=1.25, id=3),
                Order(order_type=OperationType.SELL, ticker='GBPUSD', open_time=datetime(2024, 6, 28), open_price=1.3, units=1000, stop_loss=1.35, take_profit=1.2, id=4)
            ],
            [
                Order(order_type=OperationType.BUY, ticker='EURUSD', open_time=datetime(2024, 6, 27), open_price=1.2, units=1000, stop_loss=1.15, take_profit=1.25, id=3),
                Order(order_type=OperationType.SELL, ticker='GBPUSD', open_time=datetime(2024, 6, 28), open_price=1.3, units=1000, stop_loss=1.35, take_profit=1.2, id=4)
            ]
        )
    ]
)
def test_get_open_orders(ticket, symbol, positions, expected_open_orders):
    for pos in positions:
        if pos.id == 2:
            pos.close_time = datetime(2024, 6, 29)
    trader.positions = positions

    open_orders = trader.get_open_orders(ticket=ticket, symbol=symbol)

    assert len(open_orders) == len(expected_open_orders)
    
    for open_order, exp_open_order in zip(open_orders, expected_open_orders):
        assert open_order.id == exp_open_order.id
