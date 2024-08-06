from backbone.enums import OperationType


def rsk_rw(balance, risk_percentage, risk_reward):
    tp = balance * (risk_percentage / 100) * risk_reward
    return tp