import yaml
from backbone.utils.general_purpose import load_function
from apscheduler.schedulers.blocking import BlockingScheduler
from pytz import utc
import numpy as np

np.seterr(divide='ignore')

if __name__ == '__main__':

    root = './backbone/data'
    
    with open('configs/live_trading.yml', 'r') as file:
        strategies = yaml.safe_load(file)

    with open('configs/test_creds.yml', 'r') as file:
        creds = yaml.safe_load(file)

    scheduler = BlockingScheduler(timezone=utc)

    bot_name = 'backbone.day_per_week_trader.DayPerWeekTrader'
    configs = strategies[bot_name]

    instruments_info = configs['instruments_info']
    wfo_params = configs['wfo_params']
    opt_params = configs['opt_params']

    
    for ticker, info in instruments_info.items():

        cron = info['cron']
        timeframe = info['timeframe']
        contract_volume = info['contract_volume']

        bot = load_function(bot_name)(ticker, timeframe, contract_volume, creds, opt_params, wfo_params)
        
        bot.run()
