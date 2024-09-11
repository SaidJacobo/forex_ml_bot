import time
from datetime import datetime, timedelta
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd
import pytz

from backbone.realtime_trader import RealtimeTrader
pd.set_option('display.max_columns', 500) # number of columns to be displayed
pd.set_option('display.width', 1500)      # max table width to display

def wait_for_next_execution(interval_minutes):
    """Espera hasta que sea el siguiente múltiplo de `interval_minutes`."""
    now = datetime.now()
    next_execution = (now + timedelta(minutes=interval_minutes - (now.minute % interval_minutes))).replace(second=0, microsecond=0)
    seconds_to_wait = (next_execution - now).total_seconds()
    time.sleep(seconds_to_wait)  


def execute_at_interval(interval_minutes, function):
    while True:
        function()  #                                       <---- ADVERTENCIA Esto deberia ir abajo del sleep para ir a prod


        wait_for_next_execution(interval_minutes)
        current_time = datetime.now()
        print(f"Ejecutando código a las: {current_time.strftime('%H:%M:%S')}")




def next():

    warm_up_bars = 500
    bars_to_trade = 10

    timezone = pytz.timezone("Etc/UTC")

    now = datetime.now(timezone)
    actual_date = datetime(
        now.year,
        now.month,
        now.day,
        now.hour,
        now.minute,
        0
    )

    date_from = actual_date - timedelta(days=bars_to_trade) - timedelta(days=warm_up_bars) 

    ticker = 'EURUSDm'

    df = TRADER.get_data(
        ticker,
        'D1', 
        date_from=date_from, 
        date_to=actual_date,
    )

    df = TRADER.calculate_indicators(df)
    
    print(df)

    # TRADER.open_order('EURUSDm', 'buy', lot=0.01)

    positions = TRADER.get_open_positions(ticker=ticker)

    TRADER.close_order(positions)


if __name__ == '__main__':

    TRADER = RealtimeTrader()

    interval_minutes = 1



    execute_at_interval(interval_minutes, function=next)

