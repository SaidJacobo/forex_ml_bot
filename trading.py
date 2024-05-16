
import yaml
from backbone.machine_learning_agent import MachineLearningAgent
from backbone.realtime_trader import RealtimeTrader
from datetime import datetime
from backbone.utils import load_function
from backbone.botardo import Botardo
from datetime import timedelta
import os
import pytz

if __name__ == '__main__':
 # Carga de configuraciones desde archivos YAML
    data_path = './backbone/data/trading'
    symbols_path = './backbone/data/trading/symbols'
    logs_path = './backbone/data/trading/logs'
    
    if not os.path.exists(data_path):
        os.mkdir(data_path)

    if not os.path.exists(symbols_path):
        os.mkdir(symbols_path)

    if not os.path.exists(logs_path):
        os.mkdir(logs_path)

    with open('configs/live_trading.yml', 'r') as file:
        config = yaml.safe_load(file)

    mode = config['mode']
    user = config['user']
    pw = config['password']
    model_name = config['model_name']
    model = config['model']
    model_params = config['model_params']
    threshold_up = config['threshold_up']
    threshold_down = config['threshold_down']
    risk_percentage = config['risk_percentage']
    train_window = config['train_window']
    train_period = config['train_period']
    stop_loss_in_pips = config['stop_loss_in_pips']
    take_profit_in_pips = config['take_profits_in_pips']
    periods_forward_target = config['periods_forward_target']
    use_days_in_position = config['use_days_in_position']
    trading_strategy = config['trading_strategy']

    tickers = config["tickers"] 

    risk_percentage = config["risk_percentage"] 

    strategy = load_function(trading_strategy)
    trader = RealtimeTrader(
        trading_strategy=strategy,
        threshold_up=threshold_up,
        threshold_down=threshold_down,
        allowed_days_in_position=periods_forward_target if use_days_in_position else None,
        stop_loss_in_pips=stop_loss_in_pips,
        take_profit_in_pips=take_profit_in_pips,
        risk_percentage=risk_percentage,
        save_orders_path=logs_path
    )

    mla = MachineLearningAgent(tickers, model, param_grid=None)

    botardo = Botardo(
        tickers=tickers, 
        ml_agent=mla, 
        trader=trader
    )

    # set time zone to UTC
    timezone = pytz.timezone("Etc/UTC")

    now = datetime.now(timezone) - timedelta(hours=1)
    actual_date = datetime(
        now.year,
        now.month,
        now.day,
        now.hour,
        0,
        0
    )

    date_from = actual_date - timedelta(hours=train_window + 300)

    botardo.get_symbols_and_generate_indicators(
        symbols_path=symbols_path, 
        date_from=date_from,
        date_to=actual_date,
        save=True,
        force_download=True
    )

    df = botardo.generate_dataset(
        symbols_path=symbols_path, 
        period_forward_target=periods_forward_target,
        # Corre con los simbolos que ya tiene en memoria
        load_symbols_from_disk=False,
        # Necesito que conserve el target del dia de hoy que es null
        drop_nulls=False
    )
    
    train_window = timedelta(hours=train_window)

    print('='*16, 'Iniciando backtesting', '='*16)

    botardo.trading_bot_workflow(actual_date, df, train_period, train_window, periods_forward_target)
    