from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.models.order import OrderStatus
from app.schemas.user_schema import blank_to_none, validate_phone

class PaymentMethod(str, Enum):
    CARD = "card"
    PSE = "pse"
    NEQUI = "nequi"

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=99)

class OrderProductSummary(BaseModel):
    id: int
    title: str
    volume_number: int
    comic_type: str
    cover_image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    product: Optional[OrderProductSummary] = None

    model_config = ConfigDict(from_attributes=True)

class OrderCreate(BaseModel):
    items: List[OrderItemCreate] = Field(..., min_length=1, max_length=50)
    # Datos de envío del pedido. Si no llegan, se usan los guardados en el perfil.
    recipient_name: Optional[str] = Field(default=None, max_length=100)
    recipient_phone: Optional[str] = Field(default=None, max_length=20)
    shipping_address: Optional[str] = Field(default=None, max_length=255)
    shipping_city: Optional[str] = Field(default=None, max_length=80)
    shipping_department: Optional[str] = Field(default=None, max_length=80)

    @field_validator(
        "recipient_name", "recipient_phone", "shipping_address",
        "shipping_city", "shipping_department", mode="before"
    )
    @classmethod
    def strip_blank(cls, value):
        return blank_to_none(value)

    @field_validator("recipient_phone")
    @classmethod
    def check_phone(cls, value):
        return validate_phone(value)

class OrderPayment(BaseModel):
    # Pago simulado: solo se registra el método elegido, nunca datos de tarjeta
    payment_method: PaymentMethod

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class OrderCustomer(BaseModel):
    id: int
    email: str
    full_name: str

    model_config = ConfigDict(from_attributes=True)

class OrderResponse(BaseModel):
    id: int
    user_id: int
    total_amount: Decimal
    status: OrderStatus
    created_at: datetime
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    shipping_address: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_department: Optional[str] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    paid_at: Optional[datetime] = None
    items: List[OrderItemResponse]

    model_config = ConfigDict(from_attributes=True)

class AdminOrderResponse(OrderResponse):
    user: OrderCustomer
