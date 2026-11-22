from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from passlib.context import CryptContext
from app.models.user import User
from app.schemas.user_schema import UserCreate, UserLogin, UserUpdate, PasswordChange

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )
    return user

def create_user(db: Session, user_data: UserCreate) -> User:
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado."
        )
    hashed_pw = pwd_context.hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_pw,
        full_name=user_data.full_name,
        phone=user_data.phone,
        shipping_address=user_data.shipping_address,
        city=user_data.city,
        department=user_data.department
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def authenticate_user(db: Session, login_data: UserLogin) -> User:
    user = get_user_by_email(db, login_data.email)
    if not user or not pwd_context.verify(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos."
        )
    return user

def update_profile(db: Session, user: User, profile_data: UserUpdate) -> User:
    # exclude_unset: un campo que no viene en la petición no se toca
    changes = profile_data.model_dump(exclude_unset=True)
    if changes.get("full_name", "") is None:
        # El nombre es obligatorio; si llega vacío se ignora en vez de borrarlo
        changes.pop("full_name")
    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user

def change_password(db: Session, user: User, data: PasswordChange) -> None:
    if not pwd_context.verify(data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no es correcta."
        )
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe ser distinta de la actual."
        )
    user.hashed_password = pwd_context.hash(data.new_password)
    db.commit()
