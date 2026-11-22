import secrets
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User
from app.schemas.order_schema import OrderCreate, OrderPayment, OrderStatusUpdate

# Cambios de estado que puede hacer el administrador. El paso PENDING -> PAID
# lo hace el cliente con el pago simulado.
ALLOWED_TRANSITIONS = {
    OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}

# Límites contra el acaparamiento de stock con órdenes que nunca se pagan
MAX_PENDING_ORDERS_PER_USER = 2
MAX_UNITS_PER_TITLE = 5
PENDING_ORDER_TTL = timedelta(minutes=30)

def expire_stale_orders(db: Session) -> None:
    """Cancela las órdenes pendientes vencidas y devuelve su stock al inventario."""
    cutoff = datetime.now(timezone.utc) - PENDING_ORDER_TTL
    stale_orders = (
        db.query(Order)
        .filter(Order.status == OrderStatus.PENDING, Order.created_at < cutoff)
        .with_for_update(skip_locked=True)
        .all()
    )
    for order in stale_orders:
        _restore_stock(order)
        order.status = OrderStatus.CANCELLED
    if stale_orders:
        db.commit()

def _shipping_details(order_data: OrderCreate, user: User) -> dict:
    """Datos de envío del pedido: los que escribió el cliente o, si no envió una
    dirección, los de su perfil. No se mezclan para no armar direcciones inválidas."""
    if order_data.shipping_address:
        return {
            "recipient_name": order_data.recipient_name or user.full_name,
            "recipient_phone": order_data.recipient_phone or user.phone,
            "shipping_address": order_data.shipping_address,
            "shipping_city": order_data.shipping_city,
            "shipping_department": order_data.shipping_department,
        }
    return {
        "recipient_name": user.full_name,
        "recipient_phone": user.phone,
        "shipping_address": user.shipping_address,
        "shipping_city": user.city,
        "shipping_department": user.department,
    }

def create_order(db: Session, user: User, order_data: OrderCreate) -> Order:
    expire_stale_orders(db)

    pending_count = (
        db.query(Order)
        .filter(Order.user_id == user.id, Order.status == OrderStatus.PENDING)
        .count()
    )
    if pending_count >= MAX_PENDING_ORDERS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya tienes órdenes pendientes de pago. Págalas o cancélalas antes de crear otra."
        )

    units_per_product = Counter()
    for item in order_data.items:
        units_per_product[item.product_id] += item.quantity
    if any(units > MAX_UNITS_PER_TITLE for units in units_per_product.values()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Puedes comprar como máximo {MAX_UNITS_PER_TITLE} unidades de cada tomo por pedido."
        )

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
        user_id=user.id,
        total_amount=total_amount,
        status=OrderStatus.PENDING,
        **_shipping_details(order_data, user),
        items=order_items_to_create
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order

def get_user_orders(db: Session, user_id: int):
    expire_stale_orders(db)
    return db.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).all()

def get_all_orders(db: Session):
    expire_stale_orders(db)
    return db.query(Order).order_by(Order.created_at.desc()).all()

def get_order_for_user(db: Session, order_id: int, user: User) -> Order:
    expire_stale_orders(db)
    order = db.query(Order).filter(Order.id == order_id).first()
    # Se responde 404 también si la orden es de otro usuario para no revelar que existe
    if not order or (order.user_id != user.id and not user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada."
        )
    return order

def _restore_stock(order: Order) -> None:
    for item in order.items:
        item.product.stock += item.quantity

def pay_order(db: Session, order_id: int, user: User, payment: OrderPayment) -> Order:
    order = get_order_for_user(db, order_id, user)
    if order.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada.")
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta orden ya no está pendiente de pago."
        )

    order.status = OrderStatus.PAID
    order.payment_method = payment.payment_method.value
    order.payment_reference = f"SIM-{secrets.token_hex(5).upper()}"
    order.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)
    return order

def cancel_order(db: Session, order_id: int, user: User) -> Order:
    order = get_order_for_user(db, order_id, user)
    if order.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada.")
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo puedes cancelar órdenes que aún no se han pagado."
        )

    _restore_stock(order)
    order.status = OrderStatus.CANCELLED
    db.commit()
    db.refresh(order)
    return order

def update_order_status(db: Session, order_id: int, status_data: OrderStatusUpdate) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada."
        )

    new_status = status_data.status
    if new_status == order.status:
        return order
    if new_status not in ALLOWED_TRANSITIONS[order.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede pasar una orden de '{order.status.value}' a '{new_status.value}'."
        )

    if new_status == OrderStatus.CANCELLED:
        _restore_stock(order)
    if new_status == OrderStatus.PAID and not order.paid_at:
        order.paid_at = datetime.now(timezone.utc)

    order.status = new_status
    db.commit()
    db.refresh(order)
    return order
