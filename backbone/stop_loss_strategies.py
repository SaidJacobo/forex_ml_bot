from backbone.enums import OperationType
from backbone.utils.general_purpose import diff_pips


def account_percentage(balance, risk_percentage):
    sl = balance * (risk_percentage / 100)
    return sl