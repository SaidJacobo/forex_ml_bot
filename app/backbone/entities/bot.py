import uuid
from sqlalchemy import UUID, Column, Integer, Float, String, Date, create_engine
from . import Base

# Clase que representa una tabla en la base de datos
class Bot(Base):
    __tablename__ = 'Bots'  # Nombre de la tabla en la BD

    id = id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_name = Column(String, nullable=False) 
    metatrader_name = Column(String, nullable=False)
    ticker = Column(String, nullable=False)
    timeframe = Column(String, nullable=False)
    risk = Column(Float)

    def __repr__(self):
        return f"<Bot(id={self.id}, strategy_name='{self.strategy_name}', total_profit={self.total_profit})>"
    
