import uuid
from sqlalchemy import UUID, Column, Integer, Float, String, Date, create_engine
from . import Base
from sqlalchemy.orm import relationship

# Clase que representa una tabla en la base de datos
class Strategy(Base):
    __tablename__ = 'Strategies'  # Nombre de la tabla en la BD

    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    Name = Column(String, nullable=False) 
    Description = Column(String, nullable=False)

    Bot = relationship('Bot', back_populates='Strategy', lazy='joined')


    def __repr__(self):
        return f"<Strategy(id={self.Id}, name='{self.Name}', description={self.Description})>"
