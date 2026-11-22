from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.config.protection import rate_limiter
from app.config.security import create_access_token, get_current_user
from app.models.user import User
from app.schemas.user_schema import (
    UserCreate, UserLogin, UserResponse, TokenResponse, UserUpdate, PasswordChange
)
from app.controllers import user_controller

router = APIRouter(prefix="/users", tags=["Users"])

def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    # Frena la creación masiva de cuentas
    rate_limiter.check(f"register:ip:{client_ip(request)}", limit=10, window_seconds=3600)
    return user_controller.create_user(db=db, user_data=user_data)

@router.post("/login", response_model=TokenResponse)
def login_user(login_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    # Por IP frena a un atacante probando muchas cuentas; por correo, la fuerza bruta a una sola
    rate_limiter.check(f"login:ip:{client_ip(request)}", limit=20, window_seconds=300)
    rate_limiter.check(f"login:email:{login_data.email.lower()}", limit=5, window_seconds=300)
    user = user_controller.authenticate_user(db=db, login_data=login_data)
    access_token = create_access_token(user_id=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
def update_my_profile(
    profile_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return user_controller.update_profile(db=db, user=current_user, profile_data=profile_data)

@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Frena que alguien con un token robado adivine la contraseña actual a fuerza bruta
    rate_limiter.check(f"password:user:{current_user.id}", limit=5, window_seconds=900)
    user_controller.change_password(db=db, user=current_user, data=data)
