
import yaml
from backbone.machine_learning_agent import MachineLearningAgent
from backbone.trading_agent import TradingAgent
from datetime import datetime
from backbone.utils import load_function
from backbone.metabot import ABCMetaBot

class Botardo(ABCMetaBot):

  def __init__(self, tickers:list, ml_agent:MachineLearningAgent, trading_agent:TradingAgent):
    super().__init__(tickers, ml_agent, trading_agent)


