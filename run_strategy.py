import yaml
from backbone.utils.general_purpose import load_function
import numpy as np

np.seterr(divide='ignore')

if __name__ == '__main__':

    root = './backbone/data'
    
    with open('configs/live_trading.yml', 'r') as file:
        strategies = yaml.safe_load(file)

    with open('configs/test_creds.yml', 'r') as file:
        creds = yaml.safe_load(file)


    strategy_path = 'backbone.short_ibs.ShortIBS'
    bot_path = 'backbone.trader_bot.TraderBot'
    selected_ticker = 'EURUSD'
    
    configs = strategies[strategy_path]

    instruments_info = configs['instruments_info']
    wfo_params = configs['wfo_params']
    opt_params = configs['opt_params']

    
    for ticker, info in instruments_info.items():
        
        if ticker != selected_ticker:
            continue

        cron = info['cron']
        timeframe = info['timeframe']
        
        strategy = load_function(strategy_path)

        name = configs['metatrader_name']
        bot = load_function(bot_path)(name, ticker, timeframe, creds, opt_params, wfo_params, strategy)
        
        bot.run()
