import uuid
from sqlalchemy import UUID, Column, ForeignKey, Integer, Float, String, Date, create_engine
from sqlalchemy.orm import relationship

from . import Base

# Clase que representa una tabla en la base de datos
class Timeframe(Base):
    __tablename__ = 'Timeframes'  # Nombre de la tabla en la BD

    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    Name = Column(String, nullable=False)
    MetaTraderNumber = Column(Integer, nullable=False)
    Bot = relationship('Bot', back_populates='Timeframe', lazy='select')
    
    
    def __repr__(self):
        return f"<Timeframe(id={self.Id}, Name='{self.Name}', MetaTraderNumber={self.MetaTraderNumber})>"
    
