from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.database import Base, engine
from app.config.settings import settings
from app.routes import product_router, user_router, order_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Tienda de Mangas, Cómics y Manhwas",
    description="Backend MVC con FastAPI y PostgreSQL",
    version="1.0.0"
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

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "API de Manga & Comics E-commerce activa"}