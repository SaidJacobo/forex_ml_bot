import pandas as pd
from backbone.strategies import operation_management_logic, ml_strategy
from backbone.enums import ClosePositionType, OperationType, ActionType
from backbone.order import Order
import os
import sys
import pytest
from datetime import datetime, timedelta
from collections import namedtuple

# Cambia el directorio de trabajo al directorio raíz del proyecto
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(root_dir)

# Añade el directorio `src` al `sys.path`
sys.path.insert(0, os.path.join(root_dir, 'src'))


Result = namedtuple(
    'Result', ['action', 'operation_type', 'order_id', 'comment'])


@pytest.fixture
def order_buy():
    return Order(
        id=1, 
        open_time=(datetime.now() - timedelta(hours=1)).replace(minute=0, second=0, microsecond=0), 
        order_type=OperationType.BUY, 
        stop_loss=95, 
        take_profit=105, 
        open_price=100,
        ticker='EURUSD', 
        units=20
    )

@pytest.fixture
def order_sell():
    return Order(
        id=2, 
        open_time=(datetime.now() - timedelta(hours=1)).replace(minute=0, second=0, microsecond=0), 
        order_type=OperationType.SELL, 
        stop_loss=105, 
        take_profit=95, 
        open_price=100,
        ticker='EURUSD', 
        units=20
    )

today = datetime.now().replace(minute=0, second=0, microsecond=0)

@pytest.mark.parametrize("order_fixture, today, allowed_days_in_position, use_trailing_stop, only_indicator_close_buy_condition, open_price, high_price, low_price, close_price, only_indicator_close_sell_condition, model_with_indicator_open_buy_condition, only_indicator_open_buy_condition, model_with_indicator_open_sell_condition, only_indicator_open_sell_condition, expected_result", [
    # Test case 1: Close position due to allowed days in position for BUY order
    ("order_buy", today, 1, False, False, 100, 110, 90, 100, False, False, False, False, False, Result(ActionType.CLOSE, OperationType.SELL, 1, ClosePositionType.DAYS)),
    # Test case 2: Close position due to stop loss for BUY order
    ("order_buy", today, 5, False, False, 100, 110, 90, 95, False, False, False, False, False, Result(ActionType.CLOSE, OperationType.SELL, 1, ClosePositionType.STOP_LOSS)),
    # Test case 3: Close position due to take profit for BUY order
    ("order_buy", today, 5, False, False, 100, 106, 96, 100, False, False, False, False, False, Result(ActionType.CLOSE, OperationType.SELL, 1, ClosePositionType.TAKE_PROFIT)),
    # Test case 4: Wait for allowed days in position for BUY order
    ("order_buy", today, 5, False, False, 100, 104, 96, 100, False, False, False, False, False, Result(ActionType.WAIT, None, None, None)),
    # # Test case 5: Close position due to allowed days in position for SELL order
    ("order_sell", today, 1, False, False, 100, 110, 90, 100, False, False, False, False, False, Result(ActionType.CLOSE, OperationType.BUY, 2, ClosePositionType.DAYS)),
    # # Test case 6: Close position due to stop loss for SELL order
    ("order_sell", today, 5, False, False, 100, 106, 90, 106, False, False, False, False, False, Result(ActionType.CLOSE, OperationType.SELL, 2, ClosePositionType.STOP_LOSS)),
    # # Test case 7: Close position due to take profit for SELL order
    ("order_sell", today, 5, False, False, 100, 104, 90, 90, False, False, False, False, False, Result(ActionType.CLOSE, OperationType.SELL, 2, ClosePositionType.TAKE_PROFIT)),
    # # Test case 8: Wait for allowed days in position for SELL order
    ("order_sell", today, 5, False, False, 100, 104, 96, 100, False, False, False, False, False, Result(ActionType.WAIT, None, None, None)),
    # # Test case 9: Open buy position based on indicator
    (None, today, 5, False, False, 100, 110, 90, 100, False, True, True, False, False, Result(ActionType.OPEN, OperationType.BUY, None, '')),
    # # Test case 10: Open sell position based on indicator
    (None, today, 5, False, False, 100, 110, 90, 100, False, False, False, True, True, Result(ActionType.OPEN, OperationType.SELL, None, ''))
])
def test_operation_management_logic(order_fixture, today, allowed_days_in_position, use_trailing_stop, only_indicator_close_buy_condition, open_price, high_price, low_price, close_price, only_indicator_close_sell_condition, model_with_indicator_open_buy_condition, only_indicator_open_buy_condition, model_with_indicator_open_sell_condition, only_indicator_open_sell_condition, expected_result, request):
    open_order = request.getfixturevalue(
        order_fixture) if order_fixture else None
    result = operation_management_logic(
        open_order,
        today,
        allowed_days_in_position,
        use_trailing_stop,
        only_indicator_close_buy_condition,
        open_price,
        high_price,
        low_price,
        close_price,
        only_indicator_close_sell_condition,
        model_with_indicator_open_buy_condition,
        only_indicator_open_buy_condition,
        model_with_indicator_open_sell_condition,
        only_indicator_open_sell_condition
    )
    assert result == expected_result


@pytest.fixture
def no_order():
    return None

@pytest.mark.parametrize("order_fixture, actual_market_data, allowed_days_in_position, use_trailing_stop, threshold, expected_result", [
    # Test case 1: Close position due to allowed days in position for BUY order
    ("order_buy", {"pred_label": 1, "proba": 0.8, "side": 1, "Open": 100, "High": 110, "Low": 90, "Close": 100}, 1, False, 0.7, Result(ActionType.CLOSE, OperationType.SELL, 1, ClosePositionType.DAYS)),
    # Test case 2: Close position due to stop loss for BUY order
    ("order_buy", {"pred_label": 1, "proba": 0.8, "side": 1, "Open": 100, "High": 110, "Low": 90, "Close": 94}, 5, False, 0.7, Result(ActionType.CLOSE, OperationType.SELL, 1, ClosePositionType.STOP_LOSS)),
    # Test case 3: Close position due to take profit for BUY order
    ("order_buy", {"pred_label": 1, "proba": 0.8, "side": 1, "Open": 100, "High": 106, "Low": 96, "Close": 100}, 5, False, 0.7, Result(ActionType.CLOSE, OperationType.SELL, 1, ClosePositionType.TAKE_PROFIT)),
    # Test case 4: Wait for allowed days in position for BUY order
    ("order_buy", {"pred_label": 1, "proba": 0.8, "side": 1, "Open": 100, "High": 104, "Low": 96, "Close": 100}, 5, False, 0.7, Result(ActionType.WAIT, None, None, None)),
    # Test case 5: Close position due to allowed days in position for SELL order
    ("order_sell", {"pred_label": 1, "proba": 0.8, "side": -1, "Open": 100, "High": 110, "Low": 90, "Close": 100}, 1, False, 0.7, Result(ActionType.CLOSE, OperationType.BUY, 2, ClosePositionType.DAYS)),
    # Test case 6: Close position due to stop loss for SELL order
    ("order_sell", {"pred_label": 1, "proba": 0.8, "side": -1, "Open": 100, "High": 106, "Low": 90, "Close": 106}, 5, False, 0.7, Result(ActionType.CLOSE, OperationType.SELL, 2, ClosePositionType.STOP_LOSS)),
    # Test case 7: Close position due to take profit for SELL order
    ("order_sell", {"pred_label": 1, "proba": 0.8, "side": -1, "Open": 100, "High": 104, "Low": 90, "Close": 90}, 5, False, 0.7, Result(ActionType.CLOSE, OperationType.SELL, 2, ClosePositionType.TAKE_PROFIT)),
    # Test case 8: Wait for allowed days in position for SELL order
    ("order_sell", {"pred_label": 1, "proba": 0.8, "side": -1, "Open": 100, "High": 104, "Low": 96, "Close": 100}, 5, False, 0.7, Result(ActionType.WAIT, None, None, None)),
    # Test case 9: Open buy position based on indicator
    ("no_order", {"pred_label": 1, "proba": 0.8, "side": 1, "Open": 100, "High": 110, "Low": 90, "Close": 100}, 5, False, 0.7, Result(ActionType.OPEN, OperationType.BUY, None, '')),
    # Test case 10: Open sell position based on indicator
    ("no_order", {"pred_label": 1, "proba": 0.8, "side": -1, "Open": 100, "High": 110, "Low": 90, "Close": 100}, 5, False, 0.7, Result(ActionType.OPEN, OperationType.SELL, None, ''))
])
def test_ml_strategy(order_fixture, actual_market_data, allowed_days_in_position, use_trailing_stop, threshold, expected_result, request):
    open_order = request.getfixturevalue(order_fixture) if order_fixture != "no_order" else None

    # Convertir el diccionario actual_market_data a una serie
    actual_market_data_series = pd.Series(actual_market_data)

    result = ml_strategy(
        today=datetime.now().replace(minute=0, second=0, microsecond=0),
        actual_market_data=actual_market_data_series,
        orders=[open_order] if open_order else [],
        allowed_days_in_position=allowed_days_in_position,
        use_trailing_stop=use_trailing_stop,
        threshold=threshold
    )
    assert result == expected_result
