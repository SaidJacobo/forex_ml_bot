from datetime import datetime, timedelta
import os
import pandas as pd
import numpy as np
import yaml
import random

from backbone.back_tester import BackTester
from backbone.backtesting_trader import BacktestingTrader
from backbone.botardo import Botardo
from backbone.machine_learning_agent import MachineLearningAgent
from backbone.utils import load_function


def do_simulation(config_to_test, first_time):
    # Codigo de backtesting
    trading_strategy = config_to_test['trading_strategy']
    periods_forward_target = config_to_test['periods_forward_target']
    stop_loss_in_pips = config_to_test['stop_loss_in_pips']
    risk_reward_ratio = config_to_test['risk_reward_ratio']
    take_profit_in_pips = config_to_test['stop_loss_in_pips'] * config_to_test['risk_reward_ratio']
    use_trailing_stop = config_to_test['use_trailing_stop'] 
    train_period = config_to_test['train_period']
    periods_forward_target = config_to_test['periods_forward_target']
    use_days_in_position = config_to_test['use_days_in_position']
    model_name = config_to_test['models']
    train_window = config_to_test['train_window']

    results_path = f'''
        Mode_{mode}
        -Model_{model_name}
        -TrainWw_{train_window}
        -TrainPd_{train_period}
        -TradStgy_{trading_strategy.split('.')[-1]}
        -PerFwTg_{periods_forward_target}
        -SL_{stop_loss_in_pips}
        -RR_{risk_reward_ratio}
        -CloseTime_{use_days_in_position}
        -TS_{use_trailing_stop}
    '''.replace("\n", "").strip().replace(" ", "")

    orders = None

    this_experiment_path = os.path.join(iteration_path, results_path)

    # Si el experimento ya existe se toman los resultados de ahi
    for previous_iteration in os.listdir(experiments_path):
        search_experiment_path = os.path.join(experiments_path, previous_iteration, results_path)
        if os.path.exists(search_experiment_path):
            print(f'El entrenamiento con la configuracion: {results_path} ya fue realizado. Se procederá al siguiente.')
            orders_path = os.path.join(search_experiment_path, 'orders.csv')
            orders = pd.read_csv(orders_path)
            return orders, search_experiment_path

    # Sino se corre el experimento y se calculan los resultados
    strategy = load_function(trading_strategy)
    trader = BacktestingTrader(
        money=general_config['start_money'], 
        threshold=general_config['threshold'],
        trading_strategy=strategy,
        allowed_days_in_position=periods_forward_target,
        stop_loss_in_pips=stop_loss_in_pips,
        take_profit_in_pips=take_profit_in_pips,
        risk_percentage=risk_percentage,
        allowed_sessions=allowed_sessions, 
        use_trailing_stop=use_trailing_stop, 
        pips_per_value=pips_per_value, 
        trade_with=trade_with
    )

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

    backtester.start(
        start_date=date_from,
        symbols_path=symbols_path,
        train_window=train_window, 
        train_period=train_period,
        mode=mode,
        limit_date_train=limit_date_train,
        results_path=this_experiment_path,
        period_forward_target=periods_forward_target,
        undersampling=undersampling,
        save=True
    )
    
    orders, _ = backtester.botardo.trader.get_orders()
    
    return orders, this_experiment_path



if __name__ == '__main__':

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

    with open('configs/parameters.yml', 'r') as file:
        params = yaml.safe_load(file)

    with open('configs/project_config.yml', 'r') as file:
        general_config = yaml.safe_load(file)

    with open('configs/model_config.yml', 'r') as file:
        model_configs = yaml.safe_load(file)

    # Obtención de parámetros del proyecto
    date_format = '%Y-%m-%d %H:00:00'

    mode = general_config['mode']
    paralelize = general_config['paralelize']
    limit_date_train = general_config['limit_date_train']
    date_from = datetime.strptime(general_config['date_from'], date_format)
    date_to = datetime.strptime(general_config['date_to'], date_format)
    tickers = general_config["tickers"] 
    risk_percentage = general_config["risk_percentage"] 
    undersampling = general_config['undersampling']
    allowed_sessions = general_config['allowed_sessions']

    pips_per_value = general_config['pips_per_value']
    trade_with = general_config['trade_with']

    train_windows = params['train_window']
    max_window = max(train_windows)
    first_time = True

    # empieza el merequetengue

    for iteration in range(3, 6):
        iteration_path = os.path.join(experiments_path, str(iteration))
        if not os.path.exists(iteration_path):
            os.mkdir(iteration_path)

        config_result = []
        param_names = list(params.keys())
        params_to_test = list(params.keys())
        best_params = {}
        best_config_names = []

        # check para que no itere al pedo con valores fijos
        for param_name in param_names:
            if len(params[param_name]) == 1:
                best_params[param_name] = params[param_name][0]
                params_to_test.remove(param_name)

        while len(params_to_test) > 0:
            random_param = random.choice(list(params_to_test))
            params_to_test.remove(random_param)

            history = []
            sharpe_ratios = []
            exp_paths = []

            for param_value in params[random_param]:
                config_to_test = {}

                config_to_test[random_param] = param_value

                for param in param_names:
                    if param in params_to_test:
                        config_to_test[param] = random.choice(list(params[param]))
                    
                    elif param in best_params.keys():
                        config_to_test[param] = best_params[param]
                
                history.append(config_to_test)
                
                orders, experiment_path = do_simulation(config_to_test=config_to_test, first_time=first_time)
                
                first_time = False

                # Con los resultados se calcula el sharpe ratio
                annual_risk_free_rate = 0.02
                hours_per_year = 252 * 24
                hourly_risk_free_rate = (1 + annual_risk_free_rate) ** (1/hours_per_year) - 1
                mean_hourly_return = orders['profit'].mean()
                std_hourly_return = orders['profit'].std()
                sharpe_ratio_hourly = (mean_hourly_return - hourly_risk_free_rate) / std_hourly_return
                sharpe_ratio_annualized = sharpe_ratio_hourly * np.sqrt(hours_per_year)

                exp_paths.append(experiment_path)
                sharpe_ratios.append(sharpe_ratio_annualized)
            
            max_sharpe_ratio = max(sharpe_ratios)
            index = sharpe_ratios.index(max_sharpe_ratio)
            best_exp_path = exp_paths[index]
            best_params[random_param] = history[index][random_param]
            
            
            if len(params_to_test) == 0:
                with open(os.path.join(best_exp_path, 'best_params.txt'), 'w') as file:
                    for key, value in best_params.items():
                        file.write(f'{key}: {value}\n')
                
                os.rename(best_exp_path, best_exp_path + '_opt')


    print(best_params)
print('fin')
