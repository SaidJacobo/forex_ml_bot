from importlib import import_module
import itertools

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