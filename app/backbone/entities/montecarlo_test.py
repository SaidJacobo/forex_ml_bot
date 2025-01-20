import uuid
from sqlalchemy import UUID, Column, ForeignKey, Integer, Float, String, Date
from sqlalchemy.orm import relationship

from . import Base

class MontecarloTest(Base):
    __tablename__ = 'MontecarloTests'

    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    BotPerformanceId = Column(UUID(as_uuid=True), ForeignKey('BotPerformances.Id'), nullable=False)
    Simulations = Column(Integer, nullable=False)
    ThresholdRuin = Column(Float, nullable=False)

    BotPerformance = relationship('BotPerformance', back_populates='MontecarloTest', lazy='joined')
    Metrics = relationship('MetricWharehouse', back_populates='MontecarloTest', lazy='joined')

    def __repr__(self):
        return f"<MontecarloTest(id={self.Id}, BotPerformanceId='{self.BotPerformanceId}', Simulations={self.Simulations}, ThresholdRuin={self.ThresholdRuin})>"
