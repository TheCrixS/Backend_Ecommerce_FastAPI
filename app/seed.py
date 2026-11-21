"""
Crea el usuario administrador y carga el catálogo de tomos (app/data/catalog.json).

Uso dentro de Docker:
    # Administrador + catálogo (pide la contraseña sin mostrarla)
    docker compose exec backend python -m app.seed --email admin@tienda.com --name "Administrador"

    # Solo cargar o actualizar el catálogo
    docker compose exec backend python -m app.seed

Opciones:
    --email         Correo del administrador (si se omite, no se toca ningún usuario)
    --password      Contraseña (si se omite, se pide por consola)
    --no-products   No cargar el catálogo

El catálogo nunca borra tomos. Los que ya existen (mismo título y número de tomo)
conservan su stock; solo se les completa la portada si no tienen y se convierte
el precio a pesos colombianos si todavía estaba en dólares.
Las portadas se descargan de Open Library al volumen de imágenes del backend.
"""
import argparse
import getpass
import json
import urllib.request
from decimal import Decimal
from pathlib import Path
from typing import Optional

from app.config.database import Base, SessionLocal, engine
from app.config.migrations import run_migrations
from app.config.storage import UPLOADS_URL_PREFIX, save_product_image_bytes
from app.controllers.user_controller import get_user_by_email, pwd_context
from app.models import ComicType, Product, User

CATALOG_PATH = Path(__file__).parent / "data" / "catalog.json"
COVER_URL = "https://covers.openlibrary.org/b/{kind}/{value}-L.jpg?default=false"
# Precios por debajo de este valor se asumen en dólares (datos de ejemplo antiguos)
LEGACY_PRICE_LIMIT = Decimal("1000")


def create_admin(db, email: str, full_name: str, password: str) -> None:
    user = get_user_by_email(db, email)
    if user:
        if user.is_admin:
            print(f"El usuario {email} ya es administrador.")
        else:
            user.is_admin = True
            db.commit()
            print(f"El usuario {email} ya existía y ahora es administrador.")
        return

    db.add(
        User(
            email=email,
            full_name=full_name,
            hashed_password=pwd_context.hash(password),
            is_admin=True,
        )
    )
    db.commit()
    print(f"Administrador {email} creado.")


def download_cover(cover: Optional[str]) -> Optional[str]:
    """Descarga la portada (formato 'id:123' o 'isbn:978...') y devuelve su ruta pública."""
    if not cover:
        return None
    kind, value = cover.split(":", 1)
    url = COVER_URL.format(kind=kind, value=value)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "manga-store-seed/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return save_product_image_bytes(response.read())
    except Exception as exc:  # sin red, se usa la URL remota como respaldo
        print(f"  No se pudo descargar {url} ({exc}); se usará la URL remota.")
        return url


def load_catalog(db) -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    created = updated = 0

    for entry in catalog:
        data = {key: value for key, value in entry.items() if key != "cover"}
        data["comic_type"] = ComicType(data["comic_type"])
        data["price"] = Decimal(str(data["price"]))

        product = (
            db.query(Product)
            .filter(Product.title == data["title"], Product.volume_number == data["volume_number"])
            .first()
        )

        if product is None:
            print(f"+ {data['title']} #{data['volume_number']}")
            db.add(Product(**data, cover_image_url=download_cover(entry.get("cover"))))
            created += 1
            continue

        changed = False
        if product.price < LEGACY_PRICE_LIMIT:
            product.price = data["price"]
            changed = True
        if not product.cover_image_url or not product.cover_image_url.startswith(UPLOADS_URL_PREFIX):
            cover_url = download_cover(entry.get("cover"))
            if cover_url and cover_url != product.cover_image_url:
                product.cover_image_url = cover_url
                changed = True
        if changed:
            print(f"~ {data['title']} #{data['volume_number']} actualizado")
            updated += 1

    db.commit()
    print(f"Catálogo listo: {created} tomos nuevos, {updated} actualizados, {len(catalog)} en el archivo.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea el administrador y carga el catálogo de tomos.")
    parser.add_argument("--email")
    parser.add_argument("--name", default="Administrador")
    parser.add_argument("--password")
    parser.add_argument("--no-products", action="store_true")
    args = parser.parse_args()

    password = None
    if args.email:
        password = args.password or getpass.getpass("Contraseña del administrador: ")
        if not 8 <= len(password) <= 72:
            raise SystemExit("La contraseña debe tener entre 8 y 72 caracteres.")

    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
    db = SessionLocal()
    try:
        if args.email:
            create_admin(db, args.email.strip(), args.name.strip(), password)
        if not args.no_products:
            load_catalog(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
