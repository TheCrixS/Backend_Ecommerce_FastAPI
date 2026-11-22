import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

# Dígitos con espacios, guiones, paréntesis y un + inicial opcional: 300 123 4567, +57 (601) 555-1234
PHONE_REGEX = re.compile(r"^\+?[0-9][0-9\s\-()]{6,18}$")


def blank_to_none(value):
    # Un campo vacío en el formulario borra el dato en vez de guardar ""
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def validate_phone(value: Optional[str]) -> Optional[str]:
    if value is not None and not PHONE_REGEX.match(value):
        raise PydanticCustomError(
            "phone_format",
            "El teléfono solo puede tener números, espacios, guiones y un + al inicio (7 a 19 caracteres)."
        )
    return value


class ProfileFields(BaseModel):
    phone: Optional[str] = Field(default=None, max_length=20)
    shipping_address: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=80)
    department: Optional[str] = Field(default=None, max_length=80)

    @field_validator("phone", "shipping_address", "city", "department", mode="before")
    @classmethod
    def strip_blank(cls, value):
        return blank_to_none(value)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, value):
        return validate_phone(value)


class UserBase(ProfileFields):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=72)


class UserUpdate(ProfileFields):
    # Todos los campos son opcionales: solo se cambian los que llegan en la petición.
    # El correo no se edita aquí porque es el usuario con el que se inicia sesión.
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=100)

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class PasswordChange(BaseModel):
    current_password: str = Field(..., max_length=72)
    new_password: str = Field(..., min_length=8, max_length=72)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
