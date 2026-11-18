from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.schemas.order_schema import OrderCreate, OrderStatusUpdate

def create_order(db: Session, user_id: int, order_data: OrderCreate) -> Order:
    total_amount = Decimal("0.00")
    order_items_to_create = []

    for item in order_data.items:
        product = db.query(Product).filter(Product.id == item.product_id).with_for_update().first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El producto con ID {item.product_id} no existe."
            )
        if product.stock < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente para '{product.title} #{product.volume_number}'. Disponible: {product.stock}."
            )

        product.stock -= item.quantity
        line_total = product.price * item.quantity
        total_amount += line_total

        order_items_to_create.append(
            OrderItem(
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.price
            )
        )

    new_order = Order(
        user_id=user_id,
        total_amount=total_amount,
        status=OrderStatus.PENDING,
        items=order_items_to_create
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order

def get_user_orders(db: Session, user_id: int):
    return db.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).all()

def update_order_status(db: Session, order_id: int, status_data: OrderStatusUpdate) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada."
        )

    if status_data.status == OrderStatus.CANCELLED and order.status != OrderStatus.CANCELLED:
        for item in order.items:
            item.product.stock += item.quantity

    order.status = status_data.status
    db.commit()
    db.refresh(order)
    return order