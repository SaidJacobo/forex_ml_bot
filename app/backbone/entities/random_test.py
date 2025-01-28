import uuid
from sqlalchemy import UUID, Column, ForeignKey, Integer, Float, String, Date
from sqlalchemy.orm import relationship

from . import Base

class RandomTest(Base):
    __tablename__ = 'RandomTests'

    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    BotPerformanceId = Column(UUID(as_uuid=True), ForeignKey('BotPerformances.Id'), nullable=False)
    RandomTestPerformanceId = Column(UUID(as_uuid=True), ForeignKey('BotPerformances.Id'), nullable=False)
    Iterations = Column(Integer, nullable=False)

    # Relación con BotPerformance original
    BotPerformance = relationship(
        'BotPerformance',
        foreign_keys=[BotPerformanceId],
        back_populates='RandomTest',
        lazy='joined',
        uselist=False
    )

    RandomTestPerformance = relationship(
        'BotPerformance',
        foreign_keys=[RandomTestPerformanceId],
        lazy='joined',
        uselist=False
    )

    def __repr__(self):
        return (f"<RandomTest(id={self.Id}, "
                f"BotPerformanceId='{self.BotPerformanceId}', "
                f"RandomTestPerformanceId='{self.RandomTestPerformanceId}', "
                f"Iterations={self.Iterations})>")