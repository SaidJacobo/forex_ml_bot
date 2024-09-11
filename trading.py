import joblib
import yaml
from backbone.machine_learning_agent import MachineLearningAgent
from backbone.realtime_trader_old import RealtimeTrader
from datetime import datetime
from backbone.utils.general_purpose import load_function
from backbone.botardo import Botardo
from datetime import timedelta
import os
import pytz
from backbone.telegram_bot import TelegramBot
import joblib

if __name__ == '__main__':
 # Carga de configuraciones desde archivos YAML
    root = './backbone/data'
    data_path = './backbone/data/trading'
    symbols_path = './backbone/data/trading/symbols'
    logs_path = './backbone/data/trading/logs'

    if not os.path.exists(root):
        os.mkdir(root)

    if not os.path.exists(data_path):
        os.mkdir(data_path)

    if not os.path.exists(symbols_path):
        os.mkdir(symbols_path)

    if not os.path.exists(logs_path):
        os.mkdir(logs_path)

    with open('configs/live_trading.yml', 'r') as file:
        config = yaml.safe_load(file)

    pipeline_path = config['pipeline_path']
    mode = config['mode']
    user = config['user']
    pw = config['password']
    threshold = config['threshold']
    risk_percentage = config['risk_percentage']
    train_window = config['train_window']
    train_period = config['train_period']
    stop_loss_in_pips = config['stop_loss_in_pips']
    periods_forward_target = config['periods_forward_target']
    use_days_in_position = config['use_days_in_position']
    trading_strategy = config['trading_strategy']
    telegram_bot_token = config['telegram_bot_token']
    telegram_chat_id = config['telegram_chat_id']
    allowed_sessions = config['allowed_sessions']
    pips_per_value = config['pips_per_value']
    trade_with = config['trade_with']
    use_trailing_stop = config['use_trailing_stop']
    tickers = config["tickers"] 
    risk_reward_ratio = config['risk_reward_ratio']
    undersampling = config["undersampling"] 

    take_profit_in_pips = stop_loss_in_pips * risk_reward_ratio

    telegram_bot = TelegramBot(bot_token=telegram_bot_token, chat_id=telegram_chat_id)

    ml_strategy = 'backbone.utils.trading_logic.ml_strategy'
    
    logic = load_function(ml_strategy)
    strategy = load_function(trading_strategy)
    
    trader = RealtimeTrader(
        trading_strategy=strategy,
        trading_logic=logic,
        threshold=threshold,
        allowed_days_in_position=periods_forward_target if use_days_in_position else None,
        stop_loss_in_pips=stop_loss_in_pips,
        take_profit_in_pips=take_profit_in_pips,
        risk_percentage=risk_percentage,
        save_orders_path=logs_path,
        telegram_bot=telegram_bot,
        allowed_sessions=allowed_sessions,
        use_trailing_stop=use_trailing_stop,
        pips_per_value=pips_per_value,
        trade_with=trade_with
    )

    # Cargar el pipeline desde el archivo .pkl
    with open(pipeline_path, 'rb') as file:
        pipeline = joblib.load(file)

    mla = MachineLearningAgent(tickers=tickers, pipeline=pipeline)

    botardo = Botardo(
        tickers=tickers, 
        ml_agent=mla, 
        trader=trader
    )

    # set time zone to UTC
    timezone = pytz.timezone("Etc/UTC")

    # Dependiendo del server de metatrader, la fecha esta en utc pero la data en utc +3
    now = datetime.now(timezone) + timedelta(hours=2)
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
        drop_nulls=False,
        save=True
    )
    
    train_window = timedelta(hours=train_window)

    print('='*16, 'Iniciando backtesting', '='*16)

    botardo.trading_bot_workflow(
        actual_date, 
        df, 
        train_period, 
        train_window, 
        periods_forward_target, 
        undersampling=undersampling
    )
    
    # sobreescribo el pipeline recien entrenado
    # with open(pipeline_path, 'wb') as file:
    #     joblib.dump(botardo.ml_agent.pipeline, file)
    