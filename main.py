import pandas as pd
import xgboost as xgb
from machine_learning_agent import MachineLearningAgent
from trading_agent import TradingAgent
from back_tester import BackTester
import yfinance as yf
# from strategies import machine_learning_strategy
import yaml
from importlib import import_module

def load_func(dotpath : str):
    """ load function in module.  function is right-most segment """
    module_, func = dotpath.rsplit(".", maxsplit=1)
    m = import_module(module_)
    return getattr(m, func)


if __name__ == '__main__':

    with open('configs/project_config.yml', 'r') as archivo:
        config = yaml.safe_load(archivo)

    try:
        print('Intentando levantar el dataset')
        
        df = pd.read_csv(f'./data/{config["ticker"]}.csv')

        print('Dataset levantado correctamente')

    except FileNotFoundError:
        print('No se encontro el Dataset, llamando a yfinance')

        df = yf.Ticker(config['ticker']).history(period=config['period'])

        df = df.reset_index()

        df['Date'] = pd.to_datetime(df['Date'])
        df['Date'] = df['Date'].dt.date

        df.to_csv(f'./data/{config["ticker"]}.csv', index=False)

        df = pd.read_csv(f'./data/{config["ticker"]}.csv')

        print('Dataset levantado y guardado correctamente')
    
    print(df.sample(5))

    print('Creando target')

    days_back = config['days_back_target']
    df['target'] = ((df['Close'].shift(-days_back) - df['Close']) / df['Close']) * 100
    df['target'] = df['target'].round(0)

    bins = [-25, 0, 25]
    labels = [0, 1]

    df['target'] = pd.cut(df['target'], bins, labels=labels)

    strategy = load_func(config["trading_strategy"])
    trading_agent = TradingAgent(
        start_money=config['start_money'], 
        trading_strategy=strategy,
        threshold_up=config['threshold_up'],
        threshold_down=config['threshold_down']
    )

    param_grid = {
        "model__objective": config['param_grid']['objective'],
        "model__max_depth": config['param_grid']['max_depth'],
        "model__n_estimators": config['param_grid']['n_estimators'],
        "model__learning_rate": config['param_grid']['learning_rate']
    }

    model = xgb.XGBClassifier(random_state=42)
    
    only_one_tunning = config['only_one_tunning']
    mla = MachineLearningAgent(model, param_grid, only_one_tunning=only_one_tunning)

    back_tester = BackTester(
        market_data=df, 
        ml_agent=mla, 
        trading_agent=trading_agent
    )

    back_tester.start(
        train_window=config['train_window'], 
        train_period=config['train_period']
    )
