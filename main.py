import pandas as pd
from machine_learning_agent import MachineLearningAgent
from trading_agent import TradingAgent
from back_tester import BackTester
import yfinance as yf
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

    ticker = config["ticker"] 
    try:
        print('Intentando levantar el dataset')
        
        df = pd.read_csv(f'./data/{ticker}.csv')
        df['Date'] = pd.to_datetime(df['Date'])

        print('Dataset levantado correctamente')

    except FileNotFoundError:
        print('No se encontro el Dataset, llamando a yfinance')

        df = yf.Ticker(config['ticker']).history(period=config['period'])

        df = df.reset_index()

        df['Date'] = pd.to_datetime(df['Date'])
        df['Date'] = df['Date'].dt.date

        df.to_csv(f'./data/{ticker}.csv', index=False)

        df = pd.read_csv(f'./data/{ticker}.csv')
        df['Date'] = pd.to_datetime(df['Date'])

        print('Dataset levantado y guardado correctamente')
    
    print(df.sample(5))

    print('Creando target')

    days_back = config['days_back_target']
    df['target'] = ((df['Close'].shift(-days_back) - df['Close']) / df['Close']) * 100
    df['target'] = df['target'].round(0)

    bins = [-25, 0, 25]
    labels = [0, 1]

    df['target'] = pd.cut(df['target'], bins, labels=labels)

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
        
        results_path = f'{ticker}_{model_name}_train_window_{train_window}_train_period_{train_period}_trading_strategy_{trading_strategy}_only_one_tunning_{only_one_tunning}'
        path = os.path.join('data', results_path)
        
        if os.path.exists(path):
            print(f'El entrenamiento con la configuracion: {results_path} ya fue realizado. se procedera al siguiente')

        else:

            strategy = load_func(trading_strategy)
            trading_agent = TradingAgent(
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
            mla = MachineLearningAgent(model, param_grid, only_one_tunning=only_one_tunning)

            back_tester = BackTester(
                market_data=df, 
                ml_agent=mla, 
                trading_agent=trading_agent
            )

            back_tester.start(
                train_window=train_window, 
                train_period=train_period, 
                results_path=results_path
            )
