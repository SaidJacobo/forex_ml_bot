from datetime import datetime, timedelta
import pytz
import talib as ta
from backbone.trader_bot import TraderBot
from backtesting import Strategy, Backtest
import numpy as np
import MetaTrader5 as mt5
import numpy as np
import numpy as np
from sklearn.linear_model import LinearRegression
from backbone.utils.general_purpose import diff_pips, calculate_units_size


np.seterr(divide='ignore')

def optim_func_2(stats):
    equity_curve = stats._equity_curve['Equity'].values    
    x = np.arange(len(equity_curve)).reshape(-1, 1)
    reg = LinearRegression().fit(x, equity_curve)
    stability_ratio = reg.score(x, equity_curve)
    
    return (stats['Return [%]'] /  (1 + (-1*stats['Max. Drawdown [%]']))) * np.log(1 + stats['# Trades']) * stability_ratio
    
class DayPerWeek(Strategy):
    risk = 1
    day_to_buy = 3
    percentage_price_sl = 5
    sma_period = 200
    rsi_period = 2
    rsi_upper_threshold = 90
    pip_value = 0.1
    
    def init(self):
        self.sma = self.I(
            ta.SMA, self.data.Close, timeperiod=self.sma_period
        )

        self.rsi = self.I(
            ta.RSI, self.data.Close, 2
        )
        
    def next(self):
        today = self.data.index[-1]
        if self.position:
            if self.position.is_long:
                if self.rsi > self.rsi_upper_threshold:
                    self.position.close()

        else:
            # es el dia de compra, el precio esta por encima de la sma
            if today.day_of_week == self.day_to_buy and self.data.Close[-1] > self.sma[-1]:
                sl_price = self.data.Close[-1] - self.data.Close[-1] *  (self.percentage_price_sl / 100)
                
                pip_distance = diff_pips(
                    self.data.Close[-1], 
                    sl_price, 
                    pip_value=self.pip_value
                )
                
                units = calculate_units_size(
                    account_size=self.equity, 
                    risk_percentage=self.risk, 
                    stop_loss_pips=pip_distance, 
                    pip_value=self.pip_value
                )
                
                self.buy(
                    size=units,
                    sl=sl_price,
                )
    
    def next_live(self, trader:TraderBot):
        today = self.data.index[-1]
        open_positions = trader.get_open_positions()

        if open_positions:
            if open_positions[-1].type == mt5.ORDER_TYPE_BUY and self.rsi > self.rsi_upper_threshold:
                trader.close_order(open_positions[-1])

        else:
            if today.day_of_week == self.day_to_buy and self.data.Close[-1] > self.sma[-1]:
                info_tick = trader.get_info_tick()
                
                price = info_tick.ask
                sl_price = price - price *  (self.percentage_price_sl / 100)
                
                capital_to_risk = trader.equity * self.risk / 100
                units = capital_to_risk / price
                
                lots = round(units / trader.contract_volume, 2)
                
                trader.open_order(
                    type_='buy',
                    price=price,
                    sl=sl_price,
                    size=lots
                )  

class DayPerWeekTrader(TraderBot):
    
    def __init__(self, ticker, timeframe, contract_volume, creds, opt_params, wfo_params):
        name = f'DPW_{ticker}_{timeframe}'
        
        self.trader = TraderBot(
            name=name,
            ticker=ticker, 
            timeframe=timeframe, 
            creds=creds,
            contract_volume=contract_volume
        )
        
        self.opt_params = opt_params
        self.wfo_params = wfo_params
        self.opt_params['maximize'] = optim_func_2
        self.strategy = DayPerWeek
    
    def run(self):
        warmup_bars = self.wfo_params['warmup_bars']
        look_back_bars = self.wfo_params['look_back_bars']

        timezone = pytz.timezone("Etc/UTC")
        now = datetime.now(tz=timezone)
        date_from = now - timedelta(hours=look_back_bars) - timedelta(hours=warmup_bars) 
        
        print(f'excecuting run {self.trader.name} at {now}')
        
        df = self.trader.get_data(
            date_from=date_from, 
            date_to=now,
        )

        df.index = df.index.tz_localize('UTC').tz_convert('UTC')

        bt_train = Backtest(
            df, 
            self.strategy,
            commission=7e-4,
            cash=15_000, 
            margin=1/30
        )
        
        stats_training = bt_train.optimize(
            **self.opt_params
        )
        
        bt = Backtest(
            df, 
            self.strategy,
            commission=7e-4,
            cash=15_000, 
            margin=1/30
        )
        
        opt_params = {param: getattr(stats_training._strategy, param) for param in self.opt_params.keys() if param != 'maximize'}

        stats = bt.run(
            **opt_params
        )

        bt_train._results._strategy.next_live(trader=self.trader)   


