from typing import List
from pandas import DataFrame
from app.backbone.entities.bot_performance import BotPerformance
from app.backbone.entities.trade import Trade
import pandas as pd

def _performance_from_df_to_obj(
    df_performance: DataFrame, 
    date_from, 
    date_to, 
    risk, 
    method, 
    bot, 
    initial_cash, 
    metatrader_name
    ):
    performance_for_db = [BotPerformance(**row) for _, row in df_performance.iterrows()].pop()
    performance_for_db.DateFrom = date_from
    performance_for_db.DateTo = date_to
    performance_for_db.Risk = risk
    performance_for_db.Method = method
    performance_for_db.Bot = bot
    performance_for_db.InitialCash = initial_cash
    performance_for_db.MetaTraderName = metatrader_name
    
    return performance_for_db

def get_trade_df_from_db(trades: List[Trade], performance_id):
    data = [{
            'Id': trade.Id,
            'BotPerformanceId': performance_id,
            'Size': trade.Size,
            'EntryBar': trade.EntryBar,
            'ExitBar': trade.ExitBar,
            'EntryPrice': trade.EntryPrice,
            'ExitPrice': trade.ExitPrice,
            'PnL': trade.PnL,
            'ReturnPct': trade.ReturnPct,
            'EntryTime': trade.EntryTime,
            'ExitTime': trade.ExitTime,
            'Duration': trade.Duration,
            'Equity': trade.Equity,
            'TopBest': trade.TopBest,
            'TopWorst': trade.TopWorst,
        }
        for trade in trades
    ]
    
    return pd.DataFrame(data)
