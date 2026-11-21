from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.order import OrderStatus

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
    shipping_address: Optional[str] = Field(default=None, max_length=255)

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
    shipping_address: Optional[str] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    paid_at: Optional[datetime] = None
    items: List[OrderItemResponse]

    model_config = ConfigDict(from_attributes=True)

class AdminOrderResponse(OrderResponse):
    user: OrderCustomer
