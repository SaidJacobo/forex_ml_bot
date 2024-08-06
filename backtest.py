from datetime import datetime, timedelta
import yaml
import os
from backbone.machine_learning_agent import MachineLearningAgent
from backbone.backtesting_trader import BacktestingTrader
from backbone.back_tester import BackTester
from backbone.botardo import Botardo
import multiprocessing
from backbone.utils.general_purpose import load_function, get_parameter_combinations
import random


date_format = '%Y-%m-%d %H:00:00'

def initialize_backtesting():
    root = './backbone/data'
    data_path = './backbone/data/backtest'
    experiments_path = './backbone/data/backtest/experiments'
    symbols_path = './backbone/data/backtest/symbols'
    
    if not os.path.exists(root):
        os.mkdir(root)

    # Carga de configuraciones desde archivos YAML
    if not os.path.exists(data_path):
        os.mkdir(data_path)

    if not os.path.exists(experiments_path):
        os.mkdir(experiments_path)

    if not os.path.exists(symbols_path):
        os.mkdir(symbols_path)

    with open('configs/project_config.yml', 'r') as file:
        config = yaml.safe_load(file)
    
    with open('configs/parameters.yml', 'r') as file:
        parameters = yaml.safe_load(file)
    
    with open('configs/model_config.yml', 'r') as file:
        model_configs = yaml.safe_load(file)

    # Obtención de parámetros del proyecto
    mode = config['mode']
    limit_date_train = config['limit_date_train']
    date_from = datetime.strptime(config['date_from'], date_format)
    date_to = datetime.strptime(config['date_to'], date_format)
    tickers = config["tickers"] 
    undersampling = config['undersampling']
    allowed_sessions = config['allowed_sessions']

    pips_per_value = config['pips_per_value']
    trade_with = config['trade_with']
    
    # Obtención de parámetros de entrenamiento
    models = parameters['models']
    train_window = parameters['train_window']
    train_period = parameters['train_period']
    trading_strategies = parameters['trading_strategy']
    stop_loss_strategies = parameters['stop_loss_strategies']
    take_profit_strategies = parameters['take_profit_strategies']
    periods_forward_target = parameters['periods_forward_target']
    stop_loses_in_pips = parameters['stop_loss_in_pips']
    risk_reward_ratios = parameters['risk_reward_ratio']
    intervals = parameters['intervals']
    trades_to_increment_risks = parameters['trades_to_increment_risks']
    leverages = parameters['leverages']
    risk_percentages = parameters["risk_percentages"] 


    max_window = max(train_window)

    # Combinaciones de parámetros
    parameter_combinations = get_parameter_combinations(
        models, 
        train_window, 
        train_period, 
        trading_strategies, 
        stop_loss_strategies, 
        take_profit_strategies, 
        periods_forward_target, 
        stop_loses_in_pips, 
        risk_reward_ratios,
        intervals,
        trades_to_increment_risks,
        leverages,
        risk_percentages
    )

    random.shuffle(parameter_combinations)

    first_time = True

    for combination in parameter_combinations:
        (
            model_name, 
            train_window, 
            train_period, 
            trading_strategy, 
            stop_loss_strategy, 
            take_profit_strategy, 
            period_forward_target, 
            stop_loss_in_pips, 
            risk_reward_ratio, 
            interval,
            trades_to_increment_risk,
            leverage,
            risk_percentage
        ) = combination

        # Definición de la ruta de resultados
        if model_name:
            results_path = f'''
                Model_{model_name}
                -TrainWw_{train_window}
                -TrainPd_{train_period}
                -TradStgy_{trading_strategy.split('.')[-1]}
                -SLStgy_{stop_loss_strategy.split('.')[-1]}
                -TPStgy_{take_profit_strategy.split('.')[-1]}
                -PerFwTg_{period_forward_target}
                -SL_{stop_loss_in_pips}
                -RR_{risk_reward_ratio}
                -INT_{interval}
                -TTIR_{trades_to_increment_risk}
                -Lev_{leverage}
                -RP_{risk_percentage}
            '''.replace("\n", "").strip().replace(" ", "")
        else:
            results_path = f'''
                TradStgy_{trading_strategy.split('.')[-1]}
                -SLStgy_{stop_loss_strategy.split('.')[-1]}
                -TPStgy_{take_profit_strategy.split('.')[-1]}
                -PerFwTg_{period_forward_target}
                -SL_{stop_loss_in_pips}
                -RR_{risk_reward_ratio}
                -INT_{interval}
                -TTIR_{trades_to_increment_risk}
                -Lev_{leverage}
                -RP_{risk_percentage}
            '''.replace("\n", "").strip().replace(" ", "")

        this_experiment_path = os.path.join(experiments_path, results_path)
        
        if os.path.exists(this_experiment_path):
            print(f'El entrenamiento con la configuracion: {results_path} ya fue realizado. Se procederá al siguiente.')
            continue

        print(f'Se ejecutara la configuracion {results_path}')
        
        # Carga del agente de estrategia de trading
        ml_strategy = 'backbone.utils.grid_trading_logic.ml_strategy'
        only_strategy = 'backbone.utils.grid_trading_logic.only_strategy'
        trading_logic = ml_strategy if model_name else only_strategy
        
        strategy = load_function(trading_strategy)
        logic = load_function(trading_logic)
        sl_strategy = load_function(stop_loss_strategy)
        tp_strategy = load_function(take_profit_strategy)


        trader = BacktestingTrader(
            money=config['start_money'], 
            trading_strategy=strategy,
            stop_loss_strategy=sl_strategy,
            take_profit_strategy=tp_strategy,
            trading_logic=logic,
            threshold=config['threshold'],
            allowed_days_in_position=period_forward_target,
            stop_loss_in_pips=stop_loss_in_pips,
            risk_reward=risk_reward_ratio,
            risk_percentage=risk_percentage,
            allowed_sessions=allowed_sessions, 
            pips_per_value=pips_per_value, 
            trade_with=trade_with,
            interval=interval,
            trades_to_increment_risk=trades_to_increment_risk,
            leverage=leverage,
        )

        # Configuración del modelo de machine learning
        model = None
        mla = None
        param_grid = None

        if model_name is not None:
            param_grid = model_configs[model_name]['param_grid']
            model = model_configs[model_name]['model']
            mla = MachineLearningAgent(tickers=tickers, model=model, param_grid=param_grid)

        # Inicio del backtesting
        botardo = Botardo(
            tickers=tickers, 
            ml_agent=mla, 
            trader=trader
        )
        
        backtester = BackTester(botardo)

        # si hay menos archivos de symbolos csv que la cantidad de tickers con la que trabajo
        botardo.get_symbols_and_generate_indicators(
            symbols_path=symbols_path, 
            date_from=date_from - timedelta(hours=max_window),
            date_to=date_to,
            # Si no se guarda el dataset se descargara por cada configuracion
            save=first_time,
            # No se sobreescribe para poder correr varias veces con el mismo dataset
            force_download=first_time,
        )

        first_time = False

        backtester.start(
            start_date=date_from,
            symbols_path=symbols_path,
            train_window=train_window, 
            train_period=train_period,
            mode=mode,
            limit_date_train=limit_date_train,
            results_path=this_experiment_path, 
            period_forward_target=period_forward_target,
            undersampling=undersampling
        )



if __name__ == '__main__':
    initialize_backtesting()
 
