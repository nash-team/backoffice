from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from domain.models.user import User, UserCreate
from infrastructure.database import get_db
from infrastructure.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def get_auth_service() -> AuthService:
    db = next(get_db())
    return AuthService(db)


# Dépendances au niveau du module
oauth2_scheme_dep = Depends()
auth_service_dep = Depends(get_auth_service)


@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = oauth2_scheme_dep,
    auth_service: AuthService = auth_service_dep,
):
    # OAuth2 utilise 'username' comme champ, mais nous l'utilisons pour l'email
    email = form_data.username
    user = auth_service.authenticate_user(email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth_service.create_access_token({"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=User)
async def register_user(
    user: UserCreate,
    auth_service: AuthService = auth_service_dep,
):
    try:
        return auth_service.register_user(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
