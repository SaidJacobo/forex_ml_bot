from sqlalchemy.orm import declarative_base

Base = declarative_base()

from .ticker import Ticker
from .category import Category
from .strategy import Strategy
from .timeframe import Timeframe
from .bot_performance import BotPerformance
from .bot import Bot