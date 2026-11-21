from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile, status
from app.config.storage import delete_local_image, save_product_image
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
        pattern = f"%{search}%"
        query = query.filter(or_(Product.title.ilike(pattern), Product.author.ilike(pattern)))
    # Orden estable para que la paginación con skip/limit no repita ni salte tomos
    return query.order_by(Product.title, Product.volume_number, Product.id).offset(skip).limit(limit).all()

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

    if "cover_image_url" in update_fields and update_fields["cover_image_url"] != product.cover_image_url:
        delete_local_image(product.cover_image_url)

    for field, value in update_fields.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product

def delete_product(db: Session, product_id: int) -> dict:
    product = get_product_by_id(db, product_id)
    # Los tomos con pedidos se conservan para no romper el historial de órdenes
    if product.order_items:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar este tomo porque ya tiene pedidos registrados. Puedes dejar su stock en 0 para retirarlo de la venta."
        )
    image_url = product.cover_image_url
    db.delete(product)
    db.commit()
    delete_local_image(image_url)
    return {"message": "Producto eliminado correctamente."}

async def upload_product_image(db: Session, product_id: int, file: UploadFile) -> Product:
    product = get_product_by_id(db, product_id)
    new_url = await save_product_image(file)
    previous_url = product.cover_image_url
    product.cover_image_url = new_url
    db.commit()
    db.refresh(product)
    delete_local_image(previous_url)
    return product

def remove_product_image(db: Session, product_id: int) -> Product:
    product = get_product_by_id(db, product_id)
    delete_local_image(product.cover_image_url)
    product.cover_image_url = None
    db.commit()
    db.refresh(product)
    return product