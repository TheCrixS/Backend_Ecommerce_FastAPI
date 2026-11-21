from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.config.security import get_current_admin
from app.models.product import ComicType
from app.models.user import User
from app.schemas.product_schema import ProductCreate, ProductUpdate, ProductResponse
from app.controllers import product_controller

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("/", response_model=List[ProductResponse])
def list_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    comic_type: Optional[ComicType] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    return product_controller.get_products(
        db=db,
        skip=skip,
        limit=limit,
        comic_type=comic_type,
        search=search
    )

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return product_controller.get_product_by_id(db=db, product_id=product_id)

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    return product_controller.create_product(db=db, product_data=product_data)

@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    return product_controller.update_product(
        db=db,
        product_id=product_id,
        product_data=product_data
    )

@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    return product_controller.delete_product(db=db, product_id=product_id)