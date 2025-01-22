import uuid
from sqlalchemy import UUID, Column, ForeignKey, Integer, Float, String, Date, Boolean, create_engine
from sqlalchemy.orm import relationship
from . import Base

class BotPerformance(Base):
    __tablename__ = 'BotPerformances'

    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    BotId = Column(UUID(as_uuid=True), ForeignKey('Bots.Id'), nullable=True)
    DateFrom = Column(Date, nullable=False)
    DateTo = Column(Date, nullable=False)
    Method = Column(String, nullable=False)
    StabilityRatio = Column(Float, nullable=False)
    Trades = Column(Integer, nullable=False)
    Return = Column(Float, nullable=False)
    Drawdown = Column(Float, nullable=False)
    RreturnDd = Column(Float, nullable=False)
    CustomMetric = Column(Float, nullable=False)
    WinRate = Column(Float, nullable=False)
    Duration = Column(Integer, nullable=False)
    Robust = Column(Boolean, nullable=True)
    InitialCash = Column(Float, nullable=False)

    # Relación con otras tablas
    Bot = relationship('Bot', back_populates='BotPerformance', lazy='joined')
    
    BotTradePerformance = relationship('BotTradePerformance', back_populates='BotPerformance', lazy='joined', uselist=False)
    TradeHistory = relationship('Trade', back_populates='BotPerformance', lazy='joined')
    MontecarloTest = relationship('MontecarloTest', back_populates='BotPerformance', lazy='joined', uselist=False)
    LuckTest = relationship('LuckTest', foreign_keys='LuckTest.BotPerformanceId', back_populates='BotPerformance', lazy='joined', uselist=False)
    RandomTest = relationship('RandomTest', foreign_keys='RandomTest.BotPerformanceId', back_populates='BotPerformance', lazy='joined', uselist=False)

    def __repr__(self):
        return f"<BotPerformance(Id={self.Id}, Trades={self.Trades}, Return={self.Return}, Drawdown={self.Drawdown})>"