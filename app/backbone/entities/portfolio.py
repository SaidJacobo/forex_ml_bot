import uuid
from sqlalchemy import UUID, Column, String
from . import Base
from sqlalchemy.orm import relationship

# Clase que representa una tabla en la base de datos
class Portfolio(Base):
    __tablename__ = 'Portfolios'  # Nombre de la tabla en la BD

    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    Name = Column(String, nullable=False)
    Description = Column(String, nullable=False)

    # Relación con PortfolioBacktest
    PortfolioBacktests = relationship("PortfolioBacktest", back_populates="Portfolio", lazy="select")



    def __repr__(self):
        return f"<Strategy(id={self.Id}, name='{self.Name}', description={self.Description})>"
