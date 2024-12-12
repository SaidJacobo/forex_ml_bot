import os
import sys

current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import numpy as np
from backbone.utils.general_purpose import load_function
from backbone.utils.wfo_utils import optimization_function, run_strategy, run_wfo
import os
import pandas as pd
import yaml
import os


def replace_strategy_name(obj, name):
    if isinstance(obj, dict):
        return {k: replace_strategy_name(v, name) for k, v in obj.items()}
    elif isinstance(obj, str):
        return obj.replace("{strategy_name}", name)
    return obj

if __name__ == "__main__":
    with open("./backtesting_pipeline/configs/backtest_params.yml", "r") as file_name:
        bt_params = yaml.safe_load(file_name)

    
    config_path = bt_params['config_path']
        
    with open(config_path, "r") as file_name:
        configs = yaml.safe_load(file_name)
 
    strategy_name = bt_params["strategy_name"]
    configs = replace_strategy_name(obj=configs, name=strategy_name)
        
    configs = configs["choose_the_best"]
    
    pa_path = configs["preliminar_analysis_path"]
    full_analysis_path = configs["full_analysis_path"]
    out_path = configs["out_path"]

    if not os.path.exists(out_path):
        os.makedirs(out_path)
        
    pa_filter_performance = pd.read_csv(
        os.path.join(pa_path, 'filter_performance.csv')
    )
        
    wfo_filter_performance = pd.read_csv(
        os.path.join(full_analysis_path, 'filter_performance.csv')
    )
        
    filter_performance = pd.concat(
        [pa_filter_performance, wfo_filter_performance,]
    ).sort_values(by='custom_metric', ascending=False).drop_duplicates(subset=['ticker'])
    
    filter_performance.to_csv(
        os.path.join(out_path, 'filter_performance.csv')
    )