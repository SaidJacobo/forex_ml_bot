import yaml
from backbone.utils.general_purpose import load_function
from apscheduler.schedulers.blocking import BlockingScheduler
from pytz import utc

if __name__ == '__main__':

    root = './backbone/data'
    
    with open('configs/live_trading.yml', 'r') as file:
        strategies = yaml.safe_load(file)

    scheduler = BlockingScheduler(timezone=utc)

    bot_name = 'backbone.bbands_trader.BbandsTrader'

    bot_params = strategies[bot_name]['bot_params']
    strategy_params = strategies[bot_name]['strategy_params']

    bot = load_function(bot_name)(**strategy_params)
    args = bot_params.values()
    
    bot.run(tickers=bot_params['tickers'], timeframe=bot_params['timeframe'])
