from backbone.enums import OperationType


def risk_reward(operation_type, price, risk_reward, sl_in_pips, pip_value):
      
      price_tp = None
      if operation_type == OperationType.BUY:
        price_tp = price + (risk_reward * sl_in_pips * pip_value)
      
      elif operation_type == OperationType.SELL:
        price_tp = price - (risk_reward * sl_in_pips * pip_value)
        
      return round(price_tp, 5)