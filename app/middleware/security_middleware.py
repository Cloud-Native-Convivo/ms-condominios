from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.security_config import (
    CSP_DOCS,
    CSP_ESTRICTO,
    HSTS_VALOR,
    REFERRER_POLICY,
    SERVER_NAME,
)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Agrega cabeceras de seguridad defensivas estándar HTTP a todas las respuestas."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Strict-Transport-Security"] = HSTS_VALOR
        response.headers["Referrer-Policy"] = REFERRER_POLICY

        es_documentacion = (
            request.url.path in ("/docs", "/redoc", "/openapi.json")
            or request.url.path.startswith(("/docs/", "/redoc/"))
        )
        if es_documentacion:
            response.headers["Content-Security-Policy"] = CSP_DOCS
        else:
            response.headers["Content-Security-Policy"] = CSP_ESTRICTO

        if "server" in response.headers:
            del response.headers["server"]
        response.headers["server"] = SERVER_NAME

        return response


SecurityHeadersMiddleware = SecurityMiddleware
