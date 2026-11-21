import threading
import time
from collections import defaultdict, deque
from fastapi import HTTPException, status
from starlette.types import ASGIApp, Receive, Scope, Send

# Margen sobre el límite de imagen para las cabeceras y campos del formulario multipart
BODY_OVERHEAD_BYTES = 256 * 1024


class BodySizeLimitMiddleware:
    """Rechaza con 413 los cuerpos demasiado grandes antes de que FastAPI los analice.

    FastAPI lee el formulario multipart antes de comprobar la autenticación, así que sin
    este límite cualquiera podría enviar archivos enormes a /products/{id}/image.
    """

    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                too_large = int(content_length) > self.max_bytes
            except ValueError:
                too_large = True
            if too_large:
                await self._reject(send)
                return

        # Sin Content-Length (chunked) se cuentan los bytes a medida que llegan
        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail="La petición supera el tamaño máximo permitido."
                    )
            return message

        await self.app(scope, limited_receive, send)

    async def _reject(self, send: Send) -> None:
        body = '{"detail":"La petición supera el tamaño máximo permitido."}'.encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})


class RateLimiter:
    """Ventana deslizante en memoria. Suficiente para un solo proceso de uvicorn;
    con varias réplicas habría que guardarla en Redis."""

    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                retry_after = int(window_seconds - (now - hits[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Demasiados intentos. Vuelve a intentarlo en {retry_after} segundos.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)


rate_limiter = RateLimiter()
