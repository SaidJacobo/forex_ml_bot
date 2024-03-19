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

    tickers = config["tickers"] 
    stocks = {}

    
    for ticker in tickers:
        try:
            print(f'Intentando levantar el dataset {ticker}')

            stocks[ticker] = pd.read_csv(f'./data/{ticker}.csv')

        except FileNotFoundError:
            print(f'No se encontro el Dataset {ticker}, llamando a yfinance')

            stocks[ticker] = yf.Ticker(ticker).history(period=config['period']).reset_index()
            stocks[ticker]['Date'] = stocks[ticker]['Date'].dt.date
            stocks[ticker].to_csv(f'./data/{ticker}.csv', index=False)

            print('Dataset levantado y guardado correctamente')
        
        stocks[ticker]['Date'] = pd.to_datetime(stocks[ticker]['Date'])

        print(stocks[ticker].sample(5))
        print('Creando target')

        days_back = config['days_back_target']
        stocks[ticker]['target'] = ((stocks[ticker]['Close'].shift(-days_back) - stocks[ticker]['Close']) / stocks[ticker]['Close']) * 100
        stocks[ticker]['target'] = stocks[ticker]['target'].round(0)

        bins = [-25, 0, 25]
        labels = [0, 1]

        stocks[ticker]['target'] = pd.cut(stocks[ticker]['target'], bins, labels=labels)

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
        
        results_path = f'{model_name}_train_window_{train_window}_train_period_{train_period}_trading_strategy_{trading_strategy}_only_one_tunning_{only_one_tunning}'
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
                stocks=stocks, 
                ml_agent=mla, 
                trading_agent=trading_agent
            )

            back_tester.start(
                train_window=train_window, 
                train_period=train_period, 
                results_path=results_path
            )
