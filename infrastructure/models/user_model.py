"""
Ce fichier définit le modèle UserModel pour SQLAlchemy (ORM).
Il représente la structure de la table 'users' dans la base de données.
Ce modèle est utilisé uniquement pour l'accès et la manipulation des données en base (infrastructure).
Il ne doit pas être utilisé directement dans la logique métier ou l'API.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from infrastructure.database import Base

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 