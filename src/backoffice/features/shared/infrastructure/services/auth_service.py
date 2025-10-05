import os
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backoffice.features.shared.domain.models.user import User, UserCreate
from backoffice.features.shared.infrastructure.models.user_model import UserModel

# Charger les variables d'environnement
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY n'est pas définie dans les variables d'environnement")

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        result: bool = pwd_context.verify(plain_password, hashed_password)
        return result

    def get_password_hash(self, password: str) -> str:
        result: str = pwd_context.hash(password)
        return result

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        if not SECRET_KEY:
            raise ValueError("SECRET_KEY n'est pas définie")
        encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def _convert_to_user(self, db_user: UserModel) -> User:
        return User(**dict(db_user.__dict__))

    def authenticate_user(self, email: str, password: str) -> User | None:
        db_user = self.db.query(UserModel).filter(UserModel.email == email).first()
        if not db_user:
            return None
        if not self.verify_password(password, str(db_user.hashed_password)):
            return None
        return self._convert_to_user(db_user)

    def register_user(self, user_create: UserCreate) -> User:
        # Vérifier si l'utilisateur existe déjà
        existing_user = (
            self.db.query(UserModel).filter(UserModel.email == user_create.email).first()
        )
        if existing_user:
            raise ValueError("Un utilisateur avec cet email existe déjà")

        # Créer le nouvel utilisateur
        hashed_password = self.get_password_hash(user_create.password)
        db_user = UserModel(
            email=user_create.email,
            username=user_create.username,
            hashed_password=hashed_password,
            is_active=True,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return self._convert_to_user(db_user)

    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Impossible de valider les identifiants",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            if not SECRET_KEY:
                raise credentials_exception
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if not isinstance(email, str):
                raise credentials_exception
        except JWTError as e:
            raise credentials_exception from e

        db_user = self.db.query(UserModel).filter(UserModel.email == email).first()
        if db_user is None:
            raise credentials_exception
        return self._convert_to_user(db_user)
