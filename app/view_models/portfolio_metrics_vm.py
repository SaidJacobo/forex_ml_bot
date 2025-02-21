from pydantic import BaseModel

class PortfolioPerformanceMetricsVM(BaseModel):
    StabilityRatio: float
    Return: float
    Drawdown: float
    RreturnDd: float
    PositiveHits: int
    NegativeHits: int
    MeanTimeToPositive: float
    MeanTimeToNegative: float
    StdTimeToPositive: float
    StdTimeToNegative: float