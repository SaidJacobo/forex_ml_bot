import uuid

class Order():
    def __init__(self, order_type, ticker, open_date, open_price, units, stop_loss=None, take_profit=None):
        self.id = uuid.uuid1()
        self.ticker = ticker
        self.type = order_type
        self.open_date = open_date
        self.close_date = None
        self.open_price = open_price
        self.close_price = None
        self.profit = None
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.units = units
        self.profit_in_pips = None
        self.comment=None

    def close(self, close_price, close_date, comment):
        self.close_price = close_price
        self.close_date = close_date
        self.profit_in_pips = self.get_profit()
        self.profit =  self.profit_in_pips * self.units
        self.comment=comment
        
    def get_profit(self):
        return self.open_price - self.close_price if self.type == 'sell' else self.close_price - self.open_price