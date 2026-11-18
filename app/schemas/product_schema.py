from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.product import ComicType

class ProductBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    volume_number: int = Field(default=1, ge=1)
    comic_type: ComicType
    author: str = Field(..., min_length=1, max_length=100)
    publisher: str = Field(..., min_length=1, max_length=100)
    isbn: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(default=0, ge=0)
    cover_image_url: Optional[str] = Field(default=None, max_length=255)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    volume_number: Optional[int] = Field(default=None, ge=1)
    comic_type: Optional[ComicType] = None
    author: Optional[str] = Field(default=None, min_length=1, max_length=100)
    publisher: Optional[str] = Field(default=None, min_length=1, max_length=100)
    isbn: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    stock: Optional[int] = Field(default=None, ge=0)
    cover_image_url: Optional[str] = Field(default=None, max_length=255)

class ProductResponse(ProductBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)