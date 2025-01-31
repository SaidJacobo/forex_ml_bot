import os
import subprocess
import yaml
import time
from datetime import datetime
from pytz import timezone
import logging
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta

time_frames = {
    "M1": mt5.TIMEFRAME_M1,
    "M2": mt5.TIMEFRAME_M2,
    "M3": mt5.TIMEFRAME_M3,
    "M4": mt5.TIMEFRAME_M4,
    "M5": mt5.TIMEFRAME_M5,
    "M10": mt5.TIMEFRAME_M10,
    "M12": mt5.TIMEFRAME_M12,
    "M15": mt5.TIMEFRAME_M15,
    "M20": mt5.TIMEFRAME_M20,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H2": mt5.TIMEFRAME_H2,
    "H3": mt5.TIMEFRAME_H3,
    "H4": mt5.TIMEFRAME_H4,
    "H6": mt5.TIMEFRAME_H6,
    "H8": mt5.TIMEFRAME_H8,
    "H12": mt5.TIMEFRAME_H12,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}


# Configuración del archivo YAML
CONFIG_PATH = 'configs/live_trading.yml'

# Leer las configuraciones desde el archivo YAML
def cargar_configuraciones():
    with open(CONFIG_PATH, 'r') as file:
        return yaml.safe_load(file)

# Ruta dinámica basada en la ubicación del script
def lanzar_bot(strategy_name, bot_name, ticker, timeframe, risk, opt_params, wfo_params, metatrader_name, tz):
    VENV_PYTHON_PATH = os.path.join(os.getcwd(), "mtvenv", "Scripts", "python")  # Windows
    with open(f"./logs/{bot_name}_{ticker}_{timeframe}_stdout.log", "w") as stdout_log, open(f"./logs/{bot_name}_{ticker}_{timeframe}_stderr.log", "w") as stderr_log:
        subprocess.Popen(
            [
                VENV_PYTHON_PATH,
                "bot_runner.py",
                strategy_name,
                bot_name,
                ticker,
                timeframe,
                str(risk),
                yaml.dump(opt_params) if opt_params is not None else '{}',
                yaml.dump(wfo_params) if wfo_params is not None else '{}',
                metatrader_name,
                tz
            ],
            stdout=stdout_log,
            stderr=stderr_log
        )
    print(f"[{datetime.now()}] Se lanzó el bot {bot_name} de forma asíncrona.")


# Nueva función para calcular la siguiente hora múltiplo
def siguiente_hora_multiplo(intervalo_horas, now):
    next_hour = (now.hour // intervalo_horas + 1) * intervalo_horas

    if next_hour >= 24:  # Manejar el cambio de día
        next_hour -= 24
        next_run = (now + timedelta(days=1)).replace(hour=next_hour, minute=1, second=0, microsecond=0)
    else:
        next_run = now.replace(hour=next_hour, minute=1, second=0, microsecond=0)
    
    return next_run

def ejecutar_crons():
    logger.info('Cargando configuraciones de los bots')
    configuraciones = cargar_configuraciones()
    tz = 'Etc/GMT-2'

    # Diccionario para rastrear el próximo momento de ejecución de cada bot
    proximos_runs = {}
    now = datetime.now(tz=timezone(tz))

    # Inicializar los valores de next_run para cada bot
    for strategy_name, configs in configuraciones.items():
        instruments_info = configs['instruments_info']

        for ticker, info in instruments_info.items():
            intervalo_horas = int(info['cron']['hour'].split('/')[1])
            timeframe = info['timeframe']
            proximos_runs[(strategy_name, ticker, timeframe)] = siguiente_hora_multiplo(intervalo_horas, now)

    
    while True:
        now = datetime.now(tz=timezone(tz))
        tiempo_hasta_evento = float('inf')  # Inicializar con infinito

        for strategy_name, configs in configuraciones.items():
            instruments_info = configs['instruments_info']
            bot_name = configs['name']
            metatrader_name = configs['metatrader_name']

            for ticker, info in instruments_info.items():
                cron = info['cron']
                timeframe = info['timeframe']
                risk = info['risk']

                # Recuperar el próximo momento de ejecución para este bot
                next_run = proximos_runs[(strategy_name, ticker, timeframe)]

                # Verificar si el bot debe ejecutarse
                if cron['day'] == 'mon-fri' and now.weekday() < 5:

                    if now >= next_run:

                        warmup_bars = configs['wfo_params']["warmup_bars"]
                        look_back_bars = configs['wfo_params']["look_back_bars"]
                        
                        n_bars = warmup_bars + look_back_bars
                        
                        rates = mt5.copy_rates_from_pos(
                            ticker, time_frames[timeframe], 1, n_bars
                        )
                        
                        historical_prices = pd.DataFrame(rates)
                        historical_prices["time"] = pd.to_datetime(historical_prices["time"], unit="s")

                        historical_prices = historical_prices.rename(
                            columns={
                                "time": "Date",
                                "open": "Open",
                                "high": "High",
                                "low": "Low",
                                "close": "Close",
                                "tick_volume": "Volume",
                            }
                        ).set_index("Date")
                        
                        historical_prices.to_csv(f'./live_trading_data/{metatrader_name}_{ticker}_{timeframe}.csv')
                        
                        logger.info(f'Ejecutando: {strategy_name}_{ticker}_{timeframe}_r{risk}')
                        
                        lanzar_bot(
                            strategy_name,
                            bot_name,
                            ticker,
                            timeframe,
                            risk,
                            configs['opt_params'],
                            configs['wfo_params'],
                            metatrader_name,
                            tz
                        )
                        
                        # Actualizar el próximo momento de ejecución
                        intervalo_horas = int(cron['hour'].split('/')[1])
                        proximos_runs[(strategy_name, ticker, timeframe)] = siguiente_hora_multiplo(intervalo_horas, now)

                # Actualizar el tiempo hasta el próximo evento global
                tiempo_hasta_evento = min(tiempo_hasta_evento, (next_run - now).total_seconds())

        # Dormir hasta el próximo evento global, si corresponde
        if tiempo_hasta_evento > 0 and tiempo_hasta_evento != float('inf'):
            logger.info('Proximos horarios de ejecucion:')
            
            for k, v in proximos_runs.items():
                logger.info(f'{k}: {v}')
            
            logger.info(f'A mimir {round(tiempo_hasta_evento/60)} minutos')
            
            time.sleep(tiempo_hasta_evento)



if __name__ == "__main__":
    
    if not mt5.initialize():
        quit()
    
    logger = logging.getLogger("live_trading")
    
    if not os.path.exists('./logs'):
        os.mkdir('./logs')
        
    if not os.path.exists('./live_trading_data'):
        os.mkdir('./live_trading_data')
    
    # Configuración básica de logging
    logging.basicConfig(
        level=logging.INFO,  # Nivel de logging
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Formato del mensaje
        handlers=[
            logging.FileHandler("./logs/live_trading.log"),  # Archivo donde se guardan los logs
            logging.StreamHandler()  # Mostrar también en consola
        ]
    )
    
    logger.info("Iniciando scheduler de bots utilizando subprocess...")
    ejecutar_crons()


