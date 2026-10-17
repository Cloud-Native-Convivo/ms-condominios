from dataclasses import dataclass, field
from typing import Any
from fastapi import Depends, Header, HTTPException

CSP_DOCS = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.redoc.ly; "
    "worker-src 'self' blob:; "
    "connect-src 'self'"
)

CSP_ESTRICTO = "default-src 'self'"
HSTS_VALOR = "max-age=31536000; includeSubDomains; preload"
REFERRER_POLICY = "strict-origin-when-cross-origin"
SERVER_NAME = "convivo"


def normalizar_roles(roles_raw: str | None) -> set[str]:
    """Normaliza roles a minúsculas con correspondencia bidireccional admin/administrador."""
    if not roles_raw or not roles_raw.strip():
        return set()
    roles = {r.strip().lower() for r in roles_raw.split(",") if r.strip()}
    if "administrador" in roles:
        roles.add("admin")
    if "admin" in roles:
        roles.add("administrador")
    return roles


@dataclass
class UsuarioContexto:
    """Contexto de identidad y autorización de la solicitud para ms-condominios."""
    usuario_sub: str
    roles: set[str] = field(default_factory=set)
    unidad_id: str | None = None
    condominio_id: int | None = None
    correlation_id: str | None = None

    def es_admin(self) -> bool:
        return bool({"admin", "administrador"}.intersection(self.roles))

    def es_residente(self) -> bool:
        return "residente" in self.roles

    def tiene_rol(self, rol: str) -> bool:
        rol_lower = rol.lower()
        if rol_lower in ("admin", "administrador"):
            return self.es_admin()
        return rol_lower in self.roles


def obtener_contexto_usuario(
    x_usuario_sub: str | None = Header(default=None),
    x_usuario_roles: str = Header(default=""),
    x_usuario_unidad: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
    x_condominio_id: int | None = Header(default=None),
) -> UsuarioContexto:
    """Dependencia FastAPI que extrae la identidad del llamante desde cabeceras verificadas."""
    if not x_usuario_sub or not x_usuario_sub.strip():
        raise HTTPException(
            status_code=401,
            detail="Identificador de usuario faltante o inválido",
        )
    roles = normalizar_roles(x_usuario_roles)
    return UsuarioContexto(
        usuario_sub=x_usuario_sub.strip(),
        roles=roles,
        unidad_id=x_usuario_unidad.strip() if x_usuario_unidad else None,
        condominio_id=x_condominio_id,
        correlation_id=x_correlation_id.strip() if x_correlation_id else None,
    )


def requerir_roles(roles_permitidos: list[str]):
    """Dependencia que valida roles permitidos aceptando x_usuario_roles o contexto."""
    permitidos_normalizados = set()
    for r in roles_permitidos:
        permitidos_normalizados.update(normalizar_roles(r))

    def verificador(
        x_usuario_roles: str = Header(default=""),
        contexto: UsuarioContexto | None = None,
    ) -> set[str]:
        roles = contexto.roles if contexto else normalizar_roles(x_usuario_roles)
        if not roles.intersection(permitidos_normalizados):
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        return roles

    return verificador


# Alias para mantener compatibilidad idiomática con condominios y unidades routers
requiere_roles = requerir_roles
