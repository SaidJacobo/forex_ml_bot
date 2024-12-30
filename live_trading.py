import datetime
import yaml
from backbone.utils.general_purpose import load_function
from apscheduler.schedulers.blocking import BlockingScheduler
import numpy as np
import logging
from pytz import timezone


np.seterr(divide='ignore')

timeframes = {
    'H1': 1,
    'H2': 2,
    'H3': 3,
    'H4': 4,
}

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,  # Nivel de logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Formato del mensaje
    handlers=[
        logging.FileHandler("live_trading.log"),  # Archivo donde se guardan los logs
        logging.StreamHandler()  # Mostrar también en consola
    ]
)

def siguiente_hora_multiplo(intervalo_horas, tz):
    now = datetime.datetime.now(tz=tz)    
    
    next_hour = (now.hour // intervalo_horas + 1) * intervalo_horas

    if next_hour >= 24:  # Manejar el cambio de día
        next_hour -= 24
        next_run = now.replace(day=now.day + 1, hour=next_hour, minute=0, second=0, microsecond=0)
    else:
        next_run = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
    return next_run


if __name__ == '__main__':
    logger = logging.getLogger("live_trading")

    root = './backbone/data'
    
    with open('configs/live_trading.yml', 'r') as file:
        strategies = yaml.safe_load(file)

    with open('configs/test_creds.yml', 'r') as file:
        creds = yaml.safe_load(file)

    tz = timezone('Etc/GMT-2')

    scheduler = BlockingScheduler(timezone=tz)

    bot_path = 'backbone.trader_bot.TraderBot'

    for strategy_name, configs in strategies.items():
        instruments_info = configs['instruments_info']
        wfo_params = configs['wfo_params']
        opt_params = configs['opt_params']
        metatrader_name = configs['metatrader_name']
        bot_name = configs['name']

        for ticker, info in instruments_info.items():

            cron = info['cron']
            timeframe = info['timeframe']
            risk = info['risk']
            
            start_date = siguiente_hora_multiplo(timeframes[timeframe], tz=tz)

            strategy = load_function(strategy_name)
            
            bot = load_function(bot_path)(metatrader_name, ticker, timeframe, creds, opt_params, wfo_params, strategy, risk, tz)

            scheduler.add_job(
                bot.run, 
                'cron', 
                day_of_week=cron['day'], 
                hour=cron['hour'], 
                minute=cron['minute'],
                start_date=start_date,
                misfire_grace_time=10, 
                coalesce=True
            )
            
            logger.info(f"Se ejecutará {bot_name}_{ticker}_{timeframe}_r{risk} en la fecha {start_date}")

        
    scheduler.start()