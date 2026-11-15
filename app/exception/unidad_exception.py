class UnidadException(Exception):
    pass

class UnidadNoEncontradaException(UnidadException):
    def __init__(self, id_unidad: int):
        self.id_unidad = id_unidad
        super().__init__(f"Unidad {id_unidad} no encontrada")

class UnidadIncompatibleConTipoException(UnidadException):
    """La unidad no cuadra con el tipo del condominio (Ley 21.442: A torres, B casas)."""

class UnidadInexistenteException(UnidadException):
    """La unidad pedida en una solicitud no existe (o no esta activa) en el condominio."""

    def __init__(self):
        super().__init__("La unidad no existe en este condominio")

class UnidadDuplicadaException(UnidadException):
    def __init__(self, condominio_id: int, torre: str, piso: str, numero: str):
        self.condominio_id = condominio_id
        super().__init__(
            f"Ya existe una unidad {torre}-{piso}-{numero} en el condominio {condominio_id}"
        )
