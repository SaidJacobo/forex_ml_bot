import uuid
from sqlalchemy import UUID, Column, ForeignKey, Integer, Float, String, Date, Boolean, create_engine
from sqlalchemy.orm import relationship
from . import Base           

class BotTradePerformance(Base):
    __tablename__ = 'BotTradePerformances'
    
    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    BotPerformanceId =  Column(UUID(as_uuid=True), ForeignKey('BotPerformances.Id'))
    MeanWinningReturnPct = Column(Float, nullable=False)
    StdWinningReturnPct = Column(Float, nullable=False)
    MeanLosingReturnPct = Column(Float, nullable=False)
    StdLosingReturnPct = Column(Float, nullable=False)
    MeanTradeDuration = Column(Float, nullable=False)
    StdTradeDuration = Column(Float, nullable=False)
    LongWinrate = Column(Float, nullable=False)
    WinLongMeanReturnPct = Column(Float, nullable=False)
    WinLongStdReturnPct = Column(Float, nullable=False)
    LoseLongMeanReturnPct = Column(Float, nullable=False)
    LoseLongStdReturnPct = Column(Float, nullable=False)
    ShortWinrate = Column(Float, nullable=False)
    WinShortMeanReturnPct = Column(Float, nullable=False)
    WinShortStdReturnPct = Column(Float, nullable=False)
    LoseShortMeanReturnPct = Column(Float, nullable=False)
    LoseShortStdReturnPct = Column(Float, nullable=False)

    BotPerformance = relationship('BotPerformance', back_populates='BotTradePerformance', lazy='joined')
    

    def __repr__(self):
        return f"<Timeframe(Id={self.Id}, MeanWinningReturnPct={self.MeanWinningReturnPct}, MeanTradeDuration={self.MeanTradeDuration})>"
    
    