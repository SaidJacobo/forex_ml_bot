import yaml
from backbone.utils.general_purpose import load_function
from apscheduler.schedulers.blocking import BlockingScheduler
from pytz import utc

if __name__ == '__main__':

    root = './backbone/data'
    
    with open('configs/live_trading.yml', 'r') as file:
        strategies = yaml.safe_load(file)

    with open('configs/test_creds.yml', 'r') as file:
        creds = yaml.safe_load(file)

    scheduler = BlockingScheduler(timezone=utc)

    bot_name = 'backbone.eom_trader.EndOfMonthTrader'
    configs = strategies[bot_name]

    instruments_info = configs['instruments_info']
    indicator_params = configs['indicator_params']
    strategy_params = configs['strategy_params']

    
    for ticker, info in instruments_info.items():

        cron = info['cron']
        lot_size = info['lot_size']
        timeframe = info['timeframe']

        bot = load_function(bot_name)(ticker, lot_size, timeframe, creds)
        
        cron = info['cron']
        lot_size = info['lot_size']
        timeframe = info['timeframe']
    
        bot = load_function(bot_name)(ticker, lot_size, timeframe, creds)

        bot.run(indicator_params, strategy_params)
