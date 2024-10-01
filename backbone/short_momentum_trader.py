class ShortMomentum(Strategy):
    risk = 1
    atr_multiplier = 1.5
    risk_reward = 1
    pip_value = 0.0001
    bars_in_position = 0
    max_hold_period = 5
    
    def init(self):
        self.atr = self.I(ta.ATR, self.data.High, self.data.Low, self.data.Close)
        self.adx = self.I(ta.ADX, self.data.High, self.data.Low, self.data.Close )
        self.sma = self.I(ta.SMA, self.data.Close, timeperiod=100)
        
    def next(self):
        
        if self.position:
            self.bars_in_position += 1
            
            if self.bars_in_position >= self.max_hold_period:
                self.position.close()
                self.bars_in_position = 0
        
        else:
            if self.adx[-1] < 25:
                return
            
            go_long = self.data.Close[-1] > self.sma[-1]
            
            if go_long and self.data.Close[-1] > self.data.Close[-2]:
                
                sl = self.data.Close[-1] - self.atr_multiplier * self.atr[-1]
                tp = self.data.Close[-1] + self.atr_multiplier * self.atr[-1] * self.risk_reward
                
                sl_pips = diff_pips(self.data.Close[-1], sl, pip_value=self.pip_value, absolute=True)
                account_currency_risk = self.equity * (self.risk / 100)
                units = round(account_currency_risk / (self.pip_value * sl_pips))
                
                self.buy(
                    size=units, 
                    sl=sl,
                    tp=tp
                )
            
            if not go_long and self.data.Close[-1] < self.data.Close[-2]:
                
                sl = self.data.Close[-1] + self.atr_multiplier * self.atr[-1]
                tp = self.data.Close[-1] - self.atr_multiplier * self.atr[-1] * self.risk_reward
                
                sl_pips = diff_pips(self.data.Close[-1], sl, pip_value=self.pip_value, absolute=True)
                account_currency_risk = self.equity * (self.risk / 100)
                units = round(account_currency_risk / (self.pip_value * sl_pips))
                
                self.sell(
                    size=units, 
                    sl=sl,
                    tp=tp
                )
