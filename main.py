import pandas as pd
import yaml
import os
import itertools
from importlib import import_module
from machine_learning_agent import MachineLearningAgent
from trading_agent import TradingAgent
from back_tester import BackTester

def load_function(dotpath: str):
    """Carga una función desde un módulo."""
    module_, func = dotpath.rsplit(".", maxsplit=1)
    m = import_module(module_)
    return getattr(m, func)

def get_parameter_combinations(
        models,
        train_window, 
        train_period, 
        trading_strategies, 
        periods_forward_target, 
        stop_loses_in_pips, 
        take_profits_in_pips,
        use_days_in_position
    ):
    parameter_combinations = []
    if None in models:
        strategies = [x for x in trading_strategies if x != 'strategies.ml_strategy']
        parameter_combinations += list(itertools.product(
            [None], [0], [0], strategies
        ))

        models.remove(None)
    
    parameter_combinations += list(itertools.product(
        models, 
        train_window, 
        train_period, 
        trading_strategies, 
        periods_forward_target, 
        stop_loses_in_pips, 
        take_profits_in_pips,
        use_days_in_position
    ))

    return parameter_combinations

if __name__ == '__main__':

    # Carga de configuraciones desde archivos YAML
    with open('configs/project_config.yml', 'r') as file:
        config = yaml.safe_load(file)
    
    with open('configs/parameters.yml', 'r') as file:
        parameters = yaml.safe_load(file)
    
    with open('configs/model_config.yml', 'r') as file:
        model_configs = yaml.safe_load(file)

    # Obtención de parámetros del proyecto
    period = config['period']
    mode = config['mode']
    limit_date_train = config['limit_date_train']
    date_from = config['date_from']
    date_to = config['date_to']
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
            -TrainWindow_{train_window}
            -TrainPeriod_{train_period}
            -TradingStrategy_{trading_strategy}
            -PeriodsForwardTarget_{period_forward_target}
            -SL_{stop_loss_in_pips}
            -TP_{take_profit_in_pips}
            -UseDaysInClosePos_{cancel_position_in_shift_days}
        '''.replace("\n", "").strip().replace(" ", "")
        
        print(results_path)
        
        path = os.path.join('data', results_path)
        
        if os.path.exists(path):
            print(f'El entrenamiento con la configuracion: {results_path} ya fue realizado. Se procederá al siguiente.')
            continue

        # Carga del agente de estrategia de trading
        strategy = load_function(trading_strategy)
        trading_agent = TradingAgent(
            start_money=config['start_money'], 
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
            model = load_function(model_configs[model_name]['model'])(random_state=42)
            mla = MachineLearningAgent(tickers, model, param_grid)

        # Inicio del backtesting
        back_tester = BackTester(
            tickers=tickers, 
            ml_agent=mla, 
            trading_agent=trading_agent
        )

        if not os.listdir('./data/'):
            back_tester.create_dataset(
                data_path='./data', 
                period=period,
                date_from=date_from,
                date_to=date_to
            )

        data_path = './data/dataset.csv'

        back_tester.start(
            data_path=data_path,
            train_window=train_window, 
            train_period=train_period,
            mode=mode,
            limit_date_train=limit_date_train,
            results_path=results_path, 
            period_forward_target=period_forward_target
        )
