import pandas as pd
import MetaTrader5 as mt5
import telebot
from datetime import datetime
from backtesting import Backtest
import yaml
import logging
from backbone.utils.wfo_utils import get_scaled_symbol_metadata, optimization_function

logger = logging.getLogger("TraderBot")

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

order_tpyes = {
    "buy": mt5.ORDER_TYPE_BUY,
    "sell": mt5.ORDER_TYPE_SELL,
    "buy_limit": mt5.ORDER_TYPE_BUY_LIMIT,
    "sell_limit": mt5.ORDER_TYPE_SELL_LIMIT,
}

opposite_order_tpyes = {
    mt5.ORDER_TYPE_BUY: mt5.ORDER_TYPE_SELL,
    mt5.ORDER_TYPE_SELL: mt5.ORDER_TYPE_BUY,
}


class TraderBot:

    def __init__(
        self, name:str, ticker:str, timeframe:str, creds: dict, opt_params:dict, wfo_params:dict, strategy, risk:float, timezone
    ):
        logger.info(f'inicializando {name}_{ticker}_{timeframe}_r{risk}')
        
        if not mt5.initialize():
            
            logger.info(f"initialize() failed, error code = {mt5.last_error()}")
            quit()
        
        name_ticker = ticker.split('.')[0] # --> para simbolos como us2000.cash le quito el .cash
        self.metatrader_name = f"{name}_{name_ticker}_{timeframe}"
        
        if len(self.metatrader_name) > 16:
            raise Exception(f'El nombre del bot debe tener un length menor o igual a 16: {self.metatrader_name} tiene {len(self.metatrader_name)}')
        
        bot_token = creds["telegram_bot_token"]
        chat_id = creds["telegram_chat_id"]
        server = creds["server"]
        account = creds["account"]
        pw = creds["pw"]
        
        logger.info(f'{self.metatrader_name}: Obteniendo apalancamientos para cada activo')
        with open("./configs/leverages.yml", "r") as file_name:
            self.leverages = yaml.safe_load(file_name)

        self.mt5 = mt5
        self.bot = telebot.TeleBot(bot_token)
        self.chat_id = chat_id
        self.ticker = ticker
        self.timeframe = timeframe

        self.opt_params = opt_params if opt_params != None else {}
        self.wfo_params = wfo_params
        self.strategy = strategy
        self.timezone = timezone

        logger.info(f'{self.metatrader_name}: Conectando con cuenta de Metatrader')
        authorized = self.mt5.login(server=server, login=account, password=pw)

        if authorized:
            logger.info(f'{self.metatrader_name}: Logeado correctamente en Metatrader')
            
            account_info_dict = self.mt5.account_info()._asdict()
            for prop in account_info_dict:
                logger.info("  {}={}".format(prop, account_info_dict[prop]))
        else:
            logger.info(
                "Error al logear en Metatrader #{}, error code: {}".format(
                    account, mt5.last_error()
                )
            )
            
        self.equity = account_info_dict["equity"]

        logger.info(f'{self.metatrader_name}: Obteniendo metadata de {self.ticker}')
        (
            self.scaled_pip_value,
            self.scaled_minimum_lot,
            self.scaled_maximum_lot,
            self.scaled_contract_volume,
            self.minimum_fraction,
            self.trade_tick_value_loss,
            self.volume_step,
        ) = get_scaled_symbol_metadata(ticker, metatrader=self.mt5)
        
        logger.info(f'''{self.metatrader_name}: Metadata escalada de {self.ticker}: 
            scaled_pip_value: {self.scaled_pip_value},
            scaled_minimum_lot: {self.scaled_minimum_lot},
            scaled_maximum_lot: {self.scaled_maximum_lot},
            scaled_contract_volume: {self.scaled_contract_volume},
            minimum_fraction: {self.minimum_fraction},
            trade_tick_value_loss: {self.trade_tick_value_loss},
            volume_step: {self.volume_step},  
        ''')
        
        self.opt_params["minimum_lot"] = [self.scaled_minimum_lot]
        self.opt_params["maximum_lot"] = [self.scaled_maximum_lot]
        self.opt_params["pip_value"] = [self.scaled_pip_value]
        self.opt_params["contract_volume"] = [self.scaled_contract_volume]
        self.opt_params["trade_tick_value_loss"] = [self.trade_tick_value_loss]
        self.opt_params["volume_step"] = [self.volume_step]
        self.opt_params["risk"] = [risk]

        self.opt_params["maximize"] = optimization_function
        
        logger.info(f'{self.metatrader_name}: Inicializacion completada :)')
        
    def get_data(self, n_bars=None):
        rates = self.mt5.copy_rates_from_pos(
            self.ticker, time_frames[self.timeframe], 1, n_bars
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

        return historical_prices

    def get_open_positions(self):
        logger.info(f'{self.metatrader_name}: Obteniendo posiciones abiertas')
        
        positions = self.mt5.positions_get(symbol=self.ticker)
        positions = [
            position for position in positions if position.comment == self.metatrader_name
        ]
        
        logger.info(f'{self.metatrader_name}: posiciones abiertas: {positions}')
        
        return positions

    def open_order(self, type_, price=None, sl=None, tp=None, size=None):
        
        logger.info(f'{self.metatrader_name}: abriendo nueva orden')
        
        symbol_info = self.mt5.symbol_info(self.ticker)
        if symbol_info is None:
            logger.info(f"{self.ticker}, not found, can not call order_check()")

        if not symbol_info.visible:
            logger.info(f"{self.ticker}, is not visible, trying to switch on")
            if not self.mt5.symbol_select(self.ticker, True):
                logger.info(f"symbol_select({self.ticker}) failed, exit")
        mt5_type = order_tpyes[type_]

        action = None
        action = (
            self.mt5.TRADE_ACTION_PENDING
            if mt5_type
            in [self.mt5.ORDER_TYPE_BUY_LIMIT, self.mt5.ORDER_TYPE_SELL_LIMIT]
            else self.mt5.TRADE_ACTION_DEAL
        )
        
        request = {
            "action": action,
            "symbol": self.ticker,
            "volume": size,
            "type": mt5_type,
            "price": price,
            "magic": 234000,
            "comment": f"{self.metatrader_name}",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_FOK,
        }
        
        if sl:
            request['sl'] = sl
        
        if tp:
            request['tp'] = tp
       
        logger.info(f'{self.metatrader_name}: Intentando abrir orden {request}')
       
        result_send = self.mt5.order_send(request)

        logger.info(f'{self.metatrader_name}: Resultado de la operacion {result_send}')

        if not result_send or result_send.retcode != self.mt5.TRADE_RETCODE_DONE:
            message = f"{self.metatrader_name}: fallo al abrir orden, retcode={result_send.retcode}, comment {result_send.comment}: \n"
            message += str(request)
            
            logger.info(message)
            
            try:
                logger.info(f'{self.metatrader_name}: enviando resultado por telegram')
                self.bot.send_message(chat_id=self.chat_id, text=message)
                logger.info(f'{self.metatrader_name}: Resultado enviado correctamente')
            except:
                logger.exception(f'{self.metatrader_name}: No se pudo enviar el mensaje por telegram')
                
            
        else:
            message = f"{self.metatrader_name}: Se abrio una nueva orden.  lot: {size}, price: {price}. Codigo: {result_send.retcode}"
            message += str(request)            
            logger.info('message')
            
            try:
                logger.info(f'{self.metatrader_name}: enviando resultado por telegram')
                self.bot.send_message(chat_id=self.chat_id, text=message)
                logger.info(f'{self.metatrader_name}: Resultado enviado correctamente')
            except:
                logger.exception(f'{self.metatrader_name}: No se pudo enviar el mensaje por telegram')
                
    def close_order(self, position):
        
        logger.info(f'{self.metatrader_name}: cerrando posicion {position}')
        
        close_position_type = opposite_order_tpyes[position.type]

        logger.info(f'{self.metatrader_name}: Obtenidendo precio de cierre')

        if close_position_type == order_tpyes["buy"] or order_tpyes["buy_limit"]:
            price = self.mt5.symbol_info_tick(position.symbol).ask
        else:
            price = self.mt5.symbol_info_tick(position.symbol).bid
            
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": close_position_type,
            "position": position.ticket,
            "price": price,
            "magic": 234000,
            "comment": f"{self.metatrader_name} close",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_FOK,
        }

        logger.info(f'{self.metatrader_name}: intendando cerrar orden {request}')
        
        result = self.mt5.order_send(request)
        
        logger.info(f'{self.metatrader_name}: {result}')

        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
            message = f"{self.metatrader_name}: fallo al cerrar orden retcode: {result.retcode}"
            logger.info(message)
            
            try:
                logger.info(f'{self.metatrader_name}: enviando resultado por telegram')
                self.bot.send_message(chat_id=self.chat_id, text=message)
                logger.info(f'{self.metatrader_name}: Resultado enviado correctamente')
            except:
                logger.exception(f'{self.metatrader_name}: No se pudo enviar el mensaje por telegram')
                
        else:
            message = f"{self.metatrader_name}: Orden cerrada. closed, {result}"
            logger.info(message)
            
            try:
                logger.info(f'{self.metatrader_name}: enviando resultado por telegram')
                self.bot.send_message(chat_id=self.chat_id, text=message)
                logger.info(f'{self.metatrader_name}: Resultado enviado correctamente')
                
            except:
                logger.exception(f'{self.metatrader_name}: No se pudo enviar el mensaje por telegram')

    def get_info_tick(self):
        info_tick = self.mt5.symbol_info_tick(self.ticker)
        return info_tick

    def run(self):
        
        warmup_bars = self.wfo_params["warmup_bars"]
        look_back_bars = self.wfo_params["look_back_bars"]

        logger.info(f'{self.metatrader_name}: Iniciando ejecucion')

        logger.info(f'{self.metatrader_name}: Obteniendo datos historicos')
        df = self.get_data(
            n_bars=look_back_bars + warmup_bars,
        )

        logger.info(f'{self.metatrader_name}: Datos obtenidos correctamente: {df.head(5)}')
        df.loc[:, ["Open", "High", "Low", "Close"]] = (
            df.loc[:, ["Open", "High", "Low", "Close"]] * self.minimum_fraction
        )
        
        logger.info(f'{self.metatrader_name}: Datos escalados con minimum_fraction {self.minimum_fraction}: {df.head(5)}')
        
        df.index = df.index.tz_localize("UTC").tz_convert("UTC")

        logger.info(f'{self.metatrader_name}: Obteniendo comisiones y apalancamiento para la simulacion')
        
        symbol_info = self.mt5.symbol_info_tick(self.ticker)
        avg_price = (symbol_info.bid + symbol_info.ask) / 2
        spread = symbol_info.ask - symbol_info.bid
        commission = round(spread / avg_price, 5)
        leverage = self.leverages[self.ticker]
        
        bt_train = Backtest(
            df, self.strategy, commission=commission, cash=15_000, margin=1/leverage
        )

        logger.info(f'{self.metatrader_name}: Corriendo optimizacion. opt_params: {self.opt_params}')
        stats_training = bt_train.optimize(**self.opt_params)
        
        opt_params = {
            param: getattr(stats_training._strategy, param)
            for param in self.opt_params.keys()
            if param != "maximize"
        }

        logger.info(f'{self.metatrader_name}: Optimizacion completada. Parametros optimos: {opt_params}')
        
        logger.info(f'{self.metatrader_name}: Corriendo simulacion con parametros optimos')
        bt = Backtest(df, self.strategy, commission=commission, cash=15_000, margin=1/leverage)
        _ = bt.run(**opt_params)
        
        logger.info(f'{self.metatrader_name}: Ejecutando funcion next_live') 
        bt._results._strategy.next_live(trader=self)
        