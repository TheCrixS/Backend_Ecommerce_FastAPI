import uuid
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, UploadFile, status
from app.config.settings import settings

UPLOADS_URL_PREFIX = "/uploads"
PRODUCT_IMAGES_SUBDIR = "products"

# Se valida el contenido real del archivo (firma), no la extensión ni el Content-Type del cliente
IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
}


def get_upload_root() -> Path:
    root = Path(settings.UPLOAD_DIR)
    (root / PRODUCT_IMAGES_SUBDIR).mkdir(parents=True, exist_ok=True)
    return root


def detect_image_extension(content: bytes) -> Optional[str]:
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    for signature, extension in IMAGE_SIGNATURES.items():
        if content.startswith(signature):
            return extension
    return None


def save_product_image_bytes(content: bytes) -> str:
    """Guarda la imagen con un nombre aleatorio y devuelve su ruta pública (/uploads/...)."""
    extension = detect_image_extension(content)
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no soportado. Usa una imagen JPG, PNG, WEBP o GIF."
        )
    filename = f"{uuid.uuid4().hex}.{extension}"
    (get_upload_root() / PRODUCT_IMAGES_SUBDIR / filename).write_bytes(content)
    return f"{UPLOADS_URL_PREFIX}/{PRODUCT_IMAGES_SUBDIR}/{filename}"


async def save_product_image(file: UploadFile) -> str:
    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"La imagen supera el límite de {settings.MAX_IMAGE_SIZE_MB} MB."
        )
    return save_product_image_bytes(content)


def delete_local_image(image_url: Optional[str]) -> None:
    """Borra del disco una imagen subida anteriormente (las URLs externas se ignoran)."""
    prefix = f"{UPLOADS_URL_PREFIX}/{PRODUCT_IMAGES_SUBDIR}/"
    if not image_url or not image_url.startswith(prefix):
        return
    filename = Path(image_url[len(prefix):]).name
    path = get_upload_root() / PRODUCT_IMAGES_SUBDIR / filename
    path.unlink(missing_ok=True)
