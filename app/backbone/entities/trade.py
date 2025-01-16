import uuid
from sqlalchemy import UUID, Column, ForeignKey, Integer, Float, String, Date, Boolean, create_engine
from sqlalchemy.orm import relationship
from . import Base

class Trade(Base):
    __tablename__ = 'Trades'

    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    BotPerformanceId = Column(UUID(as_uuid=True), ForeignKey('BotPerformances.Id'), nullable=False)

    Size = Column(Integer, nullable=False)
    EntryBar = Column(Integer, nullable=False)
    ExitBar = Column(Integer, nullable=False)
    EntryPrice = Column(Float, nullable=False)
    ExitPrice = Column(Float, nullable=False)
    PnL = Column(Float, nullable=False)
    ReturnPct = Column(Float, nullable=False)
    EntryTime = Column(Date, nullable=False)
    ExitTime = Column(Date, nullable=False)
    Duration = Column(Integer, nullable=False)
    Equity = Column(Float, nullable=False)

    # Relación con BotPerformance
    BotPerformance = relationship('BotPerformance', back_populates='TradeHistory', lazy='joined')

    def __repr__(self):
        return f"<TradeHistory(Id={self.Id}, Trades={self.Trades}, Return={self.Return}, Drawdown={self.Drawdown})>"
