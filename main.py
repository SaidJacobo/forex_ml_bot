import pandas as pd
from machine_learning_agent import MachineLearningAgent
from trading_agent import TradingAgent
from back_tester import BackTester
import yaml
from importlib import import_module
import itertools
import os

def load_func(dotpath : str):
    """ load function in module.  function is right-most segment """
    module_, func = dotpath.rsplit(".", maxsplit=1)
    m = import_module(module_)
    return getattr(m, func)


if __name__ == '__main__':
    
    with open('configs/project_config.yml', 'r') as archivo:
        config = yaml.safe_load(archivo)

    with open('configs/parameters.yml', 'r') as archivo:
        parameters = yaml.safe_load(archivo)

    with open('configs/model_config.yml', 'r') as archivo:
        model_configs = yaml.safe_load(archivo)

    period = config['period']
    mode = config['mode']
    limit_date_train = config['limit_date_train']
    tickers = config["tickers"] 
    days_back = config['days_back_target']
    models = parameters['models']
    train_window = parameters['train_window']
    train_period = parameters['train_period']
    trading_strategy = parameters['trading_strategy']
    only_one_tunning = parameters['only_one_tunning']

    parameter_combinations = list(itertools.product(*[
        models,
        train_window,
        train_period,
        trading_strategy,
        only_one_tunning,
        ])
    )

    for combination in parameter_combinations:
        print(combination)
        model_name, train_window, train_period, trading_strategy, only_one_tunning = combination
        
        results_path = f'{mode}_{model_name}_train_window_{train_window}_train_period_{train_period}_trading_strategy_{trading_strategy}_only_one_tunning_{only_one_tunning}'
        path = os.path.join('data', results_path)
        
        if os.path.exists(path):
            print(f'El entrenamiento con la configuracion: {results_path} ya fue realizado. se procedera al siguiente')

        else:
            strategy = load_func(trading_strategy)
            trading_agent = TradingAgent(
                tickers=tickers,
                start_money=config['start_money'], 
                trading_strategy=strategy,
                threshold_up=config['threshold_up'],
                threshold_down=config['threshold_down'],
                allowed_days_in_position=config['days_back_target']
            )

            param_grid = model_configs[model_name]['param_grid']

            model = load_func(model_configs[model_name]['model'])
            model = model(random_state=42)

            only_one_tunning = only_one_tunning
            mla = MachineLearningAgent(tickers, model, param_grid, only_one_tunning=only_one_tunning)

            back_tester = BackTester(
                tickers=tickers, 
                ml_agent=mla, 
                trading_agent=trading_agent
            )

            if not os.path.exists('./data/train.csv'):
                back_tester.create_dataset(
                    data_path='./data', 
                    days_back=days_back, 
                    period=period,
                    limit_date_train=limit_date_train
                )

            data_path = './data/train.csv' if mode == 'train' else './data/test.csv'

            back_tester.start(
                data_path=data_path,
                train_window=train_window, 
                train_period=train_period, 
                results_path=results_path
            )
