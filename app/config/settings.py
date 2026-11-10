import logging
import os
from urllib.parse import urlparse

import httpx
from pydantic_settings import BaseSettings
from sqlalchemy import URL

logger = logging.getLogger(__name__)

CONFIG_SERVER_URL = os.getenv("CONFIG_SERVER_URL", "http://localhost:8888")
_APLICACION = "ms-condominios"
_PERFIL = "native"
_ESQUEMAS_PERMITIDOS = {"http", "https"}

# Los passwords (db, rabbitmq) no se mapean: siguen solo en variables de entorno.
_MAPA_CLAVES = {
    "server.port": "PUERTO",
    "db.host": "DB_HOST",
    "db.port": "DB_PORT",
    "db.name": "DB_NAME",
    "db.username": "DB_USERNAME",
    "rabbitmq.host": "RABBITMQ_HOST",
    "rabbitmq.port": "RABBITMQ_PORT",
    "rabbitmq.usuario": "RABBITMQ_USUARIO",
    "eureka.url": "EUREKA_URL",
    "eureka.ip": "EUREKA_IP",
    "eureka.port": "EUREKA_PORT",
}


def cargar_configuracion_remota(url_base: str = CONFIG_SERVER_URL) -> None:
    """Completa variables de entorno con lo servido por config-server, sin pisar las ya definidas.

    Precedencia: variable de entorno real > config-server > default del modelo.
    Best-effort: un config-server caído no impide el arranque.
    """
    esquema = urlparse(url_base).scheme
    if esquema not in _ESQUEMAS_PERMITIDOS:
        logger.warning("CONFIG_SERVER_URL con esquema no permitido (%s) — se ignora", esquema)
        return

    try:
        respuesta = httpx.get(f"{url_base}/{_APLICACION}/{_PERFIL}", timeout=3.0)
        respuesta.raise_for_status()
    except httpx.HTTPError as error:
        logger.warning("config-server no disponible (%s) — usando configuración local", error)
        return

    for fuente in respuesta.json().get("propertySources", []):
        for clave, valor in fuente.get("source", {}).items():
            variable = _MAPA_CLAVES.get(clave)
            # Spring Cloud Config no resuelve ${...}: un valor así llegaría literal, se descarta.
            if variable and variable not in os.environ and "${" not in str(valor):
                os.environ[variable] = str(valor)


cargar_configuracion_remota()


class Settings(BaseSettings):
    # --- Base de datos Oracle ---
    db_host: str = "localhost"
    db_port: int = 1521
    db_name: str = "freepdb1"
    db_username: str = "admin"
    db_password: str  # sin default: si falta la env var, el arranque falla

    # --- RabbitMQ ---
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_usuario: str = "guest"
    rabbitmq_contrasena: str  # sin default: si falta la env var, el arranque falla

    # --- Eureka ---
    eureka_url: str = ""
    eureka_ip: str = "localhost"
    eureka_port: int = 8084

    # --- Servidor ---
    puerto: int = 8084

    @property
    def url_base_datos(self) -> URL:
        """URL async de Oracle; URL.create escapa credenciales con caracteres especiales."""
        return URL.create(
            "oracle+oracledb_async",
            username=self.db_username,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            query={"service_name": self.db_name},
        )

settings = Settings()
