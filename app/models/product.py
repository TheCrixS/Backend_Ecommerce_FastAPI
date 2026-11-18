import enum
from sqlalchemy import Column, Integer, String, Numeric, Text, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

class ComicType(str, enum.Enum):
    MANGA = "manga"       # Japón
    COMIC = "comic"       # Occidental (USA / Europa)
    MANHWA = "manhwa"     # Corea del Sur
    MANHUA = "manhua"     # China

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False, index=True)
    volume_number = Column(Integer, nullable=False, default=1)
    comic_type = Column(Enum(ComicType), nullable=False, index=True)
    author = Column(String(100), nullable=False)
    publisher = Column(String(100), nullable=False)
    isbn = Column(String(20), unique=True, nullable=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    cover_image_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order_items = relationship("OrderItem", back_populates="product")