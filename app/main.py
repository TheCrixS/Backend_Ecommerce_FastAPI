from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config.database import Base, engine
from app.config.migrations import run_migrations
from app.config.protection import BODY_OVERHEAD_BYTES, BodySizeLimitMiddleware
from app.config.settings import settings
from app.config.storage import UPLOADS_URL_PREFIX, get_upload_root
from app.routes import product_router, user_router, order_router

Base.metadata.create_all(bind=engine)
run_migrations(engine)

app = FastAPI(
    title="API Tienda de Mangas, Cómics y Manhwas",
    description="Backend MVC con FastAPI y PostgreSQL",
    version="1.1.0"
)

# Se registra antes que CORS para quedar por dentro: así el 413 también lleva cabeceras CORS
app.add_middleware(
    BodySizeLimitMiddleware,
    max_bytes=settings.MAX_IMAGE_SIZE_MB * 1024 * 1024 + BODY_OVERHEAD_BYTES,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(product_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(order_router, prefix="/api/v1")

# Portadas subidas desde el panel de administración
app.mount(UPLOADS_URL_PREFIX, StaticFiles(directory=get_upload_root()), name="uploads")

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "API de Manga & Comics E-commerce activa"}
