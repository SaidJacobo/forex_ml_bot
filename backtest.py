from datetime import datetime
import yaml
import os
from backbone.machine_learning_agent import MachineLearningAgent
from backbone.backtesting_trader import BacktestingTrader
from backbone.back_tester import BackTester
from backbone.botardo import Botardo
import multiprocessing
from backbone.utils import load_function, get_parameter_combinations

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
    paralelize = config['paralelize']
    force_download_symbols = config['force_download_symbols']
    limit_date_train = config['limit_date_train']
    date_from = datetime.strptime(config['date_from'], date_format)
    date_to = datetime.strptime(config['date_to'], date_format)
    tickers = config["tickers"] 
    risk_percentage = config["risk_percentage"] 
    
    # Obtención de parámetros de entrenamiento
    models = parameters['models']
    train_window = parameters['train_window']
    train_period = parameters['train_period']
    trading_strategies = parameters['trading_strategy']
    periods_forward_target = parameters['periods_forward_target']
    stop_loses_in_pips = parameters['stop_loss_in_pips']
    take_profits_in_pips = parameters['take_profits_in_pips']
    use_days_in_position = parameters['use_days_in_position']

    # Combinaciones de parámetros
    parameter_combinations = get_parameter_combinations(
        models, 
        train_window, 
        train_period, 
        trading_strategies, 
        periods_forward_target, 
        stop_loses_in_pips, 
        take_profits_in_pips,
        use_days_in_position
    )

    processes = []
    first_time = True
    for combination in parameter_combinations:
        (
            model_name, 
            train_window, 
            train_period, 
            trading_strategy, 
            period_forward_target, 
            stop_loss_in_pips, 
            take_profit_in_pips, 
            cancel_position_in_shift_days
        ) = combination

        # Definición de la ruta de resultados
        results_path = f'''
            Mode_{mode}
            -Model_{model_name}
            -TrainWw_{train_window}
            -TrainPd_{train_period}
            -TradingStgy_{trading_strategy.split('.')[-1]}
            -PeriodsFwTg_{period_forward_target}
            -SL_{stop_loss_in_pips}
            -TP_{take_profit_in_pips}
            -UseDaysClose_{cancel_position_in_shift_days}
        '''.replace("\n", "").strip().replace(" ", "")
        
        this_experiment_path = os.path.join(experiments_path, results_path)
        
        if os.path.exists(this_experiment_path):
            print(f'El entrenamiento con la configuracion: {results_path} ya fue realizado. Se procederá al siguiente.')
            continue

        print(f'Se ejecutara la configuracion {results_path}')
        
        # Carga del agente de estrategia de trading
        strategy = load_function(trading_strategy)
        trader = BacktestingTrader(
            money=config['start_money'], 
            trading_strategy=strategy,
            threshold_up=config['threshold_up'],
            threshold_down=config['threshold_down'],
            allowed_days_in_position=period_forward_target if cancel_position_in_shift_days else None,
            stop_loss_in_pips=stop_loss_in_pips,
            take_profit_in_pips=take_profit_in_pips,
            risk_percentage=risk_percentage,
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
            date_from=date_from,
            date_to=date_to,
            # Si no se guarda el dataset se descargara por cada configuracion
            save=first_time,
            # No se sobreescribe para poder correr varias veces con el mismo dataset
            force_download=first_time,
        )

        first_time = False

        if paralelize:
            process = multiprocessing.Process(
                target=backtester.start, 
                args=(
                    symbols_path,
                    train_window, 
                    train_period,
                    mode,
                    limit_date_train,
                    this_experiment_path, 
                    period_forward_target            
                )
            )

            processes.append(process)
        else:
            backtester.start(
                symbols_path=symbols_path,
                train_window=train_window, 
                train_period=train_period,
                mode=mode,
                limit_date_train=limit_date_train,
                results_path=this_experiment_path, 
                period_forward_target=period_forward_target
            )

    if processes:
        # Iniciar todos los procesos
        for process in processes:
            process.start()

        # Esperar a que todos los procesos terminen
        for process in processes:
            process.join()



if __name__ == '__main__':
    initialize_backtesting()
 
