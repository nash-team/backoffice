from datetime import datetime, timedelta

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from backoffice.domain.models.user import User
from backoffice.domain.ports.auth.auth_port import AuthPort
from backoffice.domain.ports.user.user_repository_port import UserRepositoryPort


class JwtAuthAdapter(AuthPort):
    def __init__(
        self,
        user_repository: UserRepositoryPort,
        secret_key: str,
        algorithm: str = "HS256",
    ):
        self.user_repository = user_repository
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        result: bool = self.pwd_context.verify(plain_password, hashed_password)
        return result

    def get_password_hash(self, password: str) -> str:
        result: str = self.pwd_context.hash(password)
        return result

    def create_access_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=30)
        to_encode.update({"exp": expire})
        result: str = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return result

    def authenticate_user(self, email: str, password: str) -> User | None:
        user = self.user_repository.get_by_email(email)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def get_current_user(self, token: str) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Impossible de valider les identifiants",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            email = payload.get("sub")
            if not isinstance(email, str):
                raise credentials_exception
        except JWTError as e:
            raise credentials_exception from e

        user = self.user_repository.get_by_email(email)
        if user is None:
            raise credentials_exception
        return user
