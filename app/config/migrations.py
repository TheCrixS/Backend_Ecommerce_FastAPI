from sqlalchemy import text
from sqlalchemy.engine import Engine

# El proyecto no usa Alembic: create_all() crea tablas nuevas pero no añade columnas
# a tablas existentes, así que estos cambios se aplican aquí de forma idempotente.
ORDER_COLUMNS = [
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipping_address VARCHAR(255)",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR(30)",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_reference VARCHAR(40)",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP WITH TIME ZONE",
]


def run_migrations(engine: Engine) -> None:
    # ALTER TYPE ... ADD VALUE no puede usarse dentro de la misma transacción que lo consulta
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'DELIVERED' AFTER 'SHIPPED'"))
        for statement in ORDER_COLUMNS:
            conn.execute(text(statement))
