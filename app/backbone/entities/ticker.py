import uuid
from sqlalchemy import UUID, Column, ForeignKey, Integer, Float, String, Date
from sqlalchemy.orm import relationship
from . import Base

# Clase que representa una tabla en la base de datos
class Ticker(Base):
    __tablename__ = 'Tickers'  # Nombre de la tabla en la BD

    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    CategoryId = Column(UUID(as_uuid=True), ForeignKey('Categories.Id'))  # Referencia a la tabla Categories
    Name = Column(String, nullable=False) 
    Commission = Column(Float, nullable=False)
    
    Category = relationship('Category', back_populates='Tickers', lazy='joined')

    def __repr__(self):
        return f"<Ticker(id={self.Id}, name='{self.Name}', commission={self.Commission})>"
