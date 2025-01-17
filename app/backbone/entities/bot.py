import uuid
from sqlalchemy import UUID, Column, ForeignKey, Integer, Float, String, Date, create_engine
from . import Base
from sqlalchemy.orm import relationship

# Clase que representa una tabla en la base de datos
class Bot(Base):
    __tablename__ = 'Bots'  # Nombre de la tabla en la BD

    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    StrategyId = Column(UUID(as_uuid=True), ForeignKey('Strategies.Id'))
    TickerId = Column(UUID(as_uuid=True), ForeignKey('Tickers.Id'))
    TimeframeId = Column(UUID(as_uuid=True), ForeignKey('Timeframes.Id'))
    Name = Column(String, nullable=False)
    MetaTraderName = Column(String(length=16), nullable=False)
    Risk = Column(Float, nullable=False)
    
    Strategy = relationship('Strategy', back_populates='Bot', lazy='joined')
    Ticker = relationship('Ticker', back_populates='Bot', lazy='joined')
    Timeframe = relationship('Timeframe', back_populates='Bot', lazy='joined')
    BotPerformance = relationship('BotPerformance', back_populates='Bot', lazy='joined', uselist=False)
    

    def __repr__(self):
        return f"<Bot(id={self.Id}, strategy_name='{self.Strategy.Id}'>"
    
