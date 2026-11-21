from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.config.security import get_current_user, get_current_admin
from app.models.user import User
from app.schemas.order_schema import (
    AdminOrderResponse,
    OrderCreate,
    OrderPayment,
    OrderResponse,
    OrderStatusUpdate,
)
from app.controllers import order_controller

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return order_controller.create_order(
        db=db,
        user=current_user,
        order_data=order_data
    )

@router.get("/", response_model=List[AdminOrderResponse])
def list_all_orders(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    return order_controller.get_all_orders(db=db)

@router.get("/me", response_model=List[OrderResponse])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return order_controller.get_user_orders(db=db, user_id=current_user.id)

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return order_controller.get_order_for_user(db=db, order_id=order_id, user=current_user)

@router.post("/{order_id}/pay", response_model=OrderResponse)
def pay_order(
    order_id: int,
    payment: OrderPayment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return order_controller.pay_order(db=db, order_id=order_id, user=current_user, payment=payment)

@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return order_controller.cancel_order(db=db, order_id=order_id, user=current_user)

@router.patch("/{order_id}/status", response_model=AdminOrderResponse)
def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    return order_controller.update_order_status(
        db=db,
        order_id=order_id,
        status_data=status_data
    )
