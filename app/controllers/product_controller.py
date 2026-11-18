from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.product import Product, ComicType
from app.schemas.product_schema import ProductCreate, ProductUpdate

def get_products(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    comic_type: Optional[ComicType] = None,
    search: Optional[str] = None
):
    query = db.query(Product)
    if comic_type:
        query = query.filter(Product.comic_type == comic_type)
    if search:
        query = query.filter(Product.title.ilike(f"%{search}%"))
    return query.offset(skip).limit(limit).all()

def get_product_by_id(db: Session, product_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El tomo o producto solicitado no existe."
        )
    return product

def create_product(db: Session, product_data: ProductCreate) -> Product:
    if product_data.isbn:
        existing_isbn = db.query(Product).filter(Product.isbn == product_data.isbn).first()
        if existing_isbn:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un producto registrado con este código ISBN."
            )
    new_product = Product(**product_data.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

def update_product(db: Session, product_id: int, product_data: ProductUpdate) -> Product:
    product = get_product_by_id(db, product_id)
    update_fields = product_data.model_dump(exclude_unset=True)

    for field, value in update_fields.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product

def delete_product(db: Session, product_id: int) -> dict:
    product = get_product_by_id(db, product_id)
    db.delete(product)
    db.commit()
    return {"message": "Producto eliminado correctamente."}