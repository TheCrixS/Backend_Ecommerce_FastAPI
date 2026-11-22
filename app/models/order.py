import enum
from sqlalchemy import Column, Integer, Numeric, ForeignKey, Enum, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Copia de los datos de envío al momento del pedido: si el usuario cambia su
    # perfil después, el pedido conserva a dónde se envió realmente
    recipient_name = Column(String(100), nullable=True)
    recipient_phone = Column(String(20), nullable=True)
    shipping_address = Column(String(255), nullable=True)
    shipping_city = Column(String(80), nullable=True)
    shipping_department = Column(String(80), nullable=True)

    # Datos del pago simulado (no se procesa dinero real)
    payment_method = Column(String(30), nullable=True)
    payment_reference = Column(String(40), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")