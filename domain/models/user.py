"""
Ce fichier définit les modèles Pydantic User pour la couche d'interface (API).
Ils servent à la validation, la sérialisation et la documentation des données
échangées via l'API (entrées/sorties).
Ils peuvent aussi servir de DTO (Data Transfer Object) entre l'infrastructure et le domaine.
Ils sont adaptés à FastAPI et facilitent la conversion entre objets Python et JSON.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    username: str
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserInDB(UserBase):
    id: int
    hashed_password: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class User(BaseModel):
    id: int
    email: EmailStr
    username: str
    hashed_password: str
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
