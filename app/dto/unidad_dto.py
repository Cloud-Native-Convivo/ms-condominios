from pydantic import BaseModel, ConfigDict, Field, field_validator


def _limpiar(v: str) -> str:
    return v.strip().upper()


def _torre_o_unica(v: object) -> object:
    """Unico campo con valor por defecto: torre vacia/ausente cae a 'UNICA'.

    Si v no es string (ni None), se devuelve sin tocar para que el chequeo de
    tipo de Pydantic lo rechace con 422 en vez de que .strip() lance AttributeError.
    """
    if v is None:
        return "UNICA"
    if not isinstance(v, str):
        return v
    limpio = _limpiar(v)
    return limpio if limpio else "UNICA"


class UnidadCrear(BaseModel):
    # condominio_id no va en el body: ya viene en la ruta (/condominios/{id_condominio}/unidades).
    torre: str = Field(default="UNICA", max_length=50)
    piso: str = Field(min_length=1, max_length=10)
    numero: str = Field(min_length=1, max_length=20)

    @field_validator("torre", mode="before")
    @classmethod
    def normalizar_torre(cls, v: str | None) -> str:
        return _torre_o_unica(v)

    @field_validator("piso", "numero", mode="before")
    @classmethod
    def normalizar_piso_numero(cls, v: str) -> str:
        # Solo limpia formato; NO aplica ningun valor por defecto.
        # Si queda vacio tras el strip, Field(min_length=1) lo rechaza con 422.
        return _limpiar(v) if isinstance(v, str) else v


class UnidadRespuesta(UnidadCrear):
    id: int
    condominio_id: int
    activa: bool
    model_config = ConfigDict(from_attributes=True)


class UnidadActualizar(BaseModel):
    torre: str | None = Field(default=None, max_length=50)
    piso: str | None = Field(default=None, min_length=1, max_length=10)
    numero: str | None = Field(default=None, min_length=1, max_length=20)
    activa: bool | None = None

    @field_validator("torre", mode="before")
    @classmethod
    def normalizar_torre(cls, v: str | None) -> str | None:
        return _torre_o_unica(v) if v is not None else None

    @field_validator("piso", "numero", mode="before")
    @classmethod
    def normalizar_piso_numero(cls, v: str | None) -> str | None:
        return _limpiar(v) if isinstance(v, str) else v
