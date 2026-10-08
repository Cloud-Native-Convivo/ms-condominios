from pydantic_settings import BaseSettings
from sqlalchemy import URL


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
