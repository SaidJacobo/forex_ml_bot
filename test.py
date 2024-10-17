from datetime import datetime
import yaml
from backbone.utils.general_purpose import load_function
from backtest.utils import plot_full_equity_curve, walk_forward
import pandas as pd


root = './backbone/data'

with open('configs/live_trading.yml', 'r') as file:
    strategies = yaml.safe_load(file)

with open('configs/test_creds.yml', 'r') as file:
    creds = yaml.safe_load(file)

date_from = datetime(2020, 1, 1)
date_to = datetime(2024, 9, 1)

not_run = [
    'backbone.eom_trader.EndOfMonthTrader',
    'backbone.vix_trader.VixTrader',    
    'backbone.b_percent_trader.BPercentTrader',
    # 'backbone.macd_trader.MacdTrader',
    'backbone.mean_reversion_trader.MeanRevTrader',
    'backbone.bbands_cross_trader.BbandsCrossTrader',
    'backbone.day_per_week_trader.DayPerWeekTrader'
]

equity_curves = {}
trades = {}

for bot_name, configs in strategies.items():

    instruments_info = configs['instruments_info']
    wfo_params = configs['wfo_params']
    opt_params = configs['opt_params']

    if bot_name in not_run:
        continue

    for ticker, info in instruments_info.items():

        timeframe = info['timeframe']
        
        name = f'{bot_name.split(".")[-1]}_{ticker}_{timeframe}'
        print(name)
        
        cron = info['cron']
        timeframe = info['timeframe']
        contract_volume = info['contract_volume']
    
        bot = load_function(bot_name)(ticker, timeframe, contract_volume, creds, opt_params, wfo_params)
        
        if bot_name == 'backbone.vix_trader.VixTrader':
            df = bot.get_full_data(date_from, date_to)
 
        else:
            df = bot.trader.get_data(date_from, date_to)
        
        
        if ticker == 'US500m' or ticker == 'USTECm' or ticker == 'US30m':
            fracc_df = df * 0.01
        else:
            fracc_df = df


        wfo_stats = walk_forward(
            bot.strategy,
            fracc_df, 
            lookback_bars=bot.wfo_params['look_back_bars'],
            validation_bars=250,
            warmup_bars=bot.wfo_params['warmup_bars'], 
            params=bot.opt_params,
            commission=7e-4, 
            margin=1/30, 
            cash=10_000,
            verbose=True
        )
        
        equity_curves[name] = wfo_stats['_equity']
        trades[name] = wfo_stats['_trades']
        
        
        
    