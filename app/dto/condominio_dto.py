from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CondominioCrear(BaseModel):
    # Límites espejo de las columnas de app/model/condominio.py
    nombre: str = Field(min_length=1, max_length=255)
    direccion: str = Field(min_length=1, max_length=255)
    tipo: Literal["A", "B"] = "A"  # Ley 21.442: condominios tipo A y tipo B
    cantidad_sectores: int = Field(default=1, gt=0)
    plan: str = Field(default="basico", min_length=1, max_length=50)
    registro_minvu: str | None = Field(default=None, max_length=255)
    seguro_incendio: bool = False
    plan_emergencia: bool = False

class CondominioRespuesta(CondominioCrear):
    id: int
    model_config = ConfigDict(from_attributes=True)

class CondominioActualizar(BaseModel):
    # Todos opcionales: actualizacion parcial, solo se aplican los campos enviados
    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    direccion: str | None = Field(default=None, min_length=1, max_length=255)
    tipo: Literal["A", "B"] | None = None
    cantidad_sectores: int | None = Field(default=None, gt=0)
    plan: str | None = Field(default=None, min_length=1, max_length=50)
    registro_minvu: str | None = None
    seguro_incendio: bool | None = None
    plan_emergencia: bool | None = None
