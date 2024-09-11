import multiprocessing
import yaml
from backbone.eom_trader import EndOfMonthTrader
from backbone.utils.general_purpose import load_function


def run_bot_in_parallel(bot_name, bot_params, strategy_params):
    # Cargar y configurar el bot
    bot = load_function(bot_name)(**strategy_params)
    # Ejecutar el bot
    bot.run(
        tickers=bot_params['tickers'], 
        timeframe=bot_params['timeframe'], 
        interval_minutes=bot_params['interval_minutes'], 
        noisy=True
    )

if __name__ == '__main__':

    root = './backbone/data'
    
    with open('configs/live_trading.yml', 'r') as file:
        strategies = yaml.safe_load(file)

    processes = []
    for bot_name, configs in strategies.items():
        bot_params = configs['bot_params']
        strategy_params = configs['strategy_params']

        # Crear un proceso separado para cada bot
        p = multiprocessing.Process(
            target=run_bot_in_parallel, 
            args=(bot_name, bot_params, strategy_params)
        )
        processes.append(p)

    # Iniciar los procesos
    for p in processes:
        p.start()

    # Esperar a que todos los procesos terminen
    for p in processes:
        p.join()

