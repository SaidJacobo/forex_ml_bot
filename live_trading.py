import multiprocessing
import yaml
from backbone.utils.general_purpose import load_function
from apscheduler.schedulers.blocking import BlockingScheduler
from pytz import utc

if __name__ == '__main__':

    root = './backbone/data'
    
    with open('configs/live_trading.yml', 'r') as file:
        strategies = yaml.safe_load(file)

    scheduler = BlockingScheduler(timezone=utc)

    for bot_name, configs in strategies.items():
        bot_params = configs['bot_params']
        strategy_params = configs['strategy_params']
        cron = configs['cron']
    
        bot = load_function(bot_name)(**strategy_params)

        scheduler.add_job(
            bot.run, 
            'cron', 
            day_of_week=cron['day'], 
            hour=cron['hour'], 
            minute=cron['minute'], 
            args=(bot_params.values())
        )
    
    scheduler.start()




