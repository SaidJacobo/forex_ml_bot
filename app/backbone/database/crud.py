from contextlib import contextmanager
from sqlalchemy import UUID
from sqlalchemy.orm import Session
from backbone.database.db import get_db
from sqlalchemy.sql import and_

class CRUDBase:
    def __init__(self, model):
        self.model = model

    def get_by_id(self, db: Session, id: int):
        return db.query(self.model).filter(self.model.id == id).first()

    def get_by_filter(self, db: Session, **filters):
        return db.query(self.model).filter(and_(*[getattr(self.model, key) == value for key, value in filters.items()])).first()
    
    def get_many_by_filter(self, db: Session, **filters):
        return db.query(self.model).filter(and_(*[getattr(self.model, key) == value for key, value in filters.items()]))
    
    def get_all(self, db: Session):
        return db.query(self.model).all()

    def create(self, db: Session, obj_in):
        db.add(obj_in)
        return obj_in

    def update(self, db: Session, obj_in):
        db_obj = db.query(self.model).filter(self.model.id == obj_in.id).first()
        db.merge(obj_in)  # Fusionar el objeto actualizado en la sesión
        return db_obj

    def delete(self, db: Session, id: UUID):
        obj = db.query(self.model).filter(self.model.id == id).first()
        if obj:
            db.delete(obj)
        return obj

    def save(self, db: Session):
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        
    @contextmanager
    def get_database(self):
        with get_db() as db:
            try:
                db.expire_on_commit=False
                yield db
                db.commit()  # Se ejecuta implícitamente al salir del contexto
    
            except Exception as e:
                db.rollback()
                raise e

