from finvizfinance.screener.overview import Overview
import pandas as pd
from backbone.utils.general_purpose import screener_columns
import yfinance as yf
import telebot
import pandas as pd
import pytz
from datetime import datetime

class Screener():
    
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.name = 'Screener'

        self.bot = telebot.TeleBot(telegram_bot_token)
        self.chat_id = telegram_chat_id

    def get_undervalued_stocks(self):
        foverview = Overview()
        
        filters_dict = {
            'P/E':'Under 25',
            'Return on Equity': 'Over +15%',
            'Return on Assets' : 'Over +15%',
            'Debt/Equity':'Under 1', 
            'Current Ratio' : 'Over 1',
            'PEG':'Low (<1)', 
        }

        foverview.set_filter(filters_dict=filters_dict)

        df_overview = foverview.screener_view()
        df_overview.to_csv('./overview.csv', index=False)
        tickers = df_overview['Ticker'].to_list()

        return tickers


    def run(self):
        
        timezone = pytz.timezone("Etc/UTC")
        now = datetime.now(tz=timezone)
        print(f'excecuting run {self.name} at {now}')

        interest_tickers = self.get_undervalued_stocks()

        # Diccionario para almacenar la información fundamental de cada ticker
        fundamental_data = {}

        # Obtener la información de cada ticker
        for ticker in interest_tickers:
            stock = yf.Ticker(ticker)
            info = stock.info  # Información fundamental
            fundamental_data[ticker] = info

        # Mostrar la información fundamental obtenida

        metrics = pd.DataFrame()
        for ticker, info in fundamental_data.items():
            stock_metrics_dict = {}
            
            for column in screener_columns:
                stock_metrics_dict[column] = [info.get(column)]

            stock_metrics = pd.DataFrame(stock_metrics_dict)
            metrics = pd.concat([metrics, stock_metrics])  

        metrics = metrics.set_index('symbol')

        doc = open('./overview.csv', 'rb')
        self.bot.send_message(chat_id=self.chat_id, text='Aqui te envio posibles oportunidades de inversion :)')
        self.bot.send_document(chat_id=self.chat_id, document=doc)

