import uuid
from sqlalchemy import UUID, Column, ForeignKey, Integer, Float, String, Date, create_engine
from sqlalchemy.orm import relationship

from . import Base

# Clase que representa una tabla en la base de datos
class Category(Base):
    __tablename__ = 'Categories'  # Cambié el nombre para evitar colisión con Tickers
    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    Name = Column(String, nullable=False) 
    
    Tickers = relationship('Ticker', back_populates='Category', lazy='joined')

    def __repr__(self):
        return f"<Category(id={self.Id}, name='{self.Name}')>"
