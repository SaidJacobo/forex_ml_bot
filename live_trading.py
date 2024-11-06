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

    bot_path = 'backbone.trader_bot.TraderBot'

    for strategy_name, configs in strategies.items():
        instruments_info = configs['instruments_info']
        wfo_params = configs['wfo_params']
        opt_params = configs['opt_params']
        name = configs['name']

        for ticker, info in instruments_info.items():

            cron = info['cron']
            timeframe = info['timeframe']

            strategy = load_function(strategy_name)
            
            bot = load_function(bot_path)(name, ticker, timeframe, creds, opt_params, wfo_params, strategy)

            scheduler.add_job(
                bot.run, 
                'cron', 
                day_of_week=cron['day'], 
                hour=cron['hour'], 
                minute=cron['minute'], 
                misfire_grace_time=10, 
                coalesce=True
            )
        
    scheduler.start()


