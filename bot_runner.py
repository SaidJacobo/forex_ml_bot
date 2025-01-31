import sys
import yaml
from datetime import datetime
from pytz import timezone
from backbone.trader_bot import TraderBot
from backbone.utils.general_purpose import load_function
import logging
import MetaTrader5 as mt5

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,  # Nivel de logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Formato del mensaje
    handlers=[
        logging.FileHandler("./logs/bot_runner.log"),  # Archivo donde se guardan los logs
        logging.StreamHandler()  # Mostrar también en consola
    ]
)

if __name__ == "__main__":
    
    logger = logging.getLogger("bot_runner")
    
    if len(sys.argv) != 10:
        logger.error("Revise los argumentos enviados al script")
        sys.exit(1)

    # Recibir parámetros desde la línea de comandos
    strategy_name = sys.argv[1]
    bot_name = sys.argv[2]
    ticker = sys.argv[3]
    timeframe = sys.argv[4]
    risk = float(sys.argv[5])
    
    opt_params = yaml.safe_load(sys.argv[6]) if sys.argv[6].strip() else {}
    wfo_params = yaml.safe_load(sys.argv[7]) if sys.argv[7].strip() else {}
    
    metatrader_name = sys.argv[8]
    tz = sys.argv[9]

    try:
        with open("./configs/test_creds.yml", "r") as file:
            creds = yaml.safe_load(file)

        strategy = load_function(strategy_name)

        bot = TraderBot(
            strategy_name=metatrader_name,
            ticker=ticker,
            timeframe=timeframe,
            creds=creds,
            opt_params=opt_params,
            wfo_params=wfo_params,
            strategy=strategy,
            risk=risk,
            timezone=timezone(tz)
        )

        bot.run()
        logger.info(f'Bot {metatrader_name}_{ticker}_{timeframe}_r{risk} ejecutado con exito :)')

    except Exception as e:
        logger.error(f"[{datetime.now(timezone('Etc/UTC'))}] Error al ejecutar el bot {bot_name}: {e}")
