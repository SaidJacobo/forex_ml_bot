import uuid
from sqlalchemy import UUID, Column, ForeignKey, String
from . import Base
from sqlalchemy.orm import relationship

# Clase que representa una tabla en la base de datos
class PortfolioBacktest(Base):
    __tablename__ = 'PortfoliosBacktests'  # Nombre de la tabla en la BD

    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    PortfolioId = Column(UUID(as_uuid=True), ForeignKey('Portfolios.Id'), primary_key=True)
    BotPerformanceId = Column(UUID(as_uuid=True), ForeignKey('BotPerformances.Id'), primary_key=True)
    Portfolio = relationship("Portfolio", back_populates="PortfolioBacktests", lazy="joined")
    BotPerformance = relationship("BotPerformance", back_populates="PortfolioBacktests", lazy="joined")




    def __repr__(self):
        return f"<Strategy(id={self.Id}, PortfolioId='{self.PortfolioId}', BotPerformanceId={self.BotPerformanceId})>"
