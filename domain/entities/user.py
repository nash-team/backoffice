"""
Ce fichier définit l'entité User du domaine métier.
Il représente l'utilisateur tel qu'il est manipulé dans la logique métier pure
(use cases, services du domaine).
Il ne dépend d'aucune technologie d'infrastructure
(ni ORM, ni Pydantic, ni base de données).
Utilisé pour garantir l'indépendance du domaine vis-à-vis des détails techniques.
"""
from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    id: Optional[int] = None
    username: str
    email: str
    hashed_password: str
    is_admin: bool = False
