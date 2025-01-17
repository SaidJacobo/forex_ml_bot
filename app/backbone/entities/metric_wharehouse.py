import uuid
from sqlalchemy import UUID, Column, ForeignKey, Integer, Float, String, Date
from sqlalchemy.orm import relationship

from . import Base

# Clase que representa una tabla en la base de datos
class MetricWharehouse(Base):
    __tablename__ = 'MetricsWarehouse'  # Nombre de la tabla en la BD

    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    BotPerformanceId = Column(UUID(as_uuid=True), ForeignKey('BotPerformances.Id'), nullable=False)
    
    Method = Column(String, nullable=False) 
    Metric = Column(String, nullable=False) 
    ColumnName = Column(String, nullable=False) 
    Value = Column(Float, nullable=False)
    
    BotPerformance = relationship('BotPerformance', back_populates='Montecarlo', lazy='joined')


    def __repr__(self):
        return f"<MetricWharehouse(id={self.Id}, Method='{self.Method}', Metric={self.Metric}, Value={self.Value})>"
