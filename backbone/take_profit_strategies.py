from backbone.enums import OperationType


def risk_reward(balance, risk_percentage, risk_reward):
    tp = balance * (risk_percentage / 100) * risk_reward
    return tp