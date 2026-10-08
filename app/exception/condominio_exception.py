class CondominioException(Exception):
    pass

class CondominioNoEncontradoException(CondominioException):
    def __init__(self, id_condominio: int):
        self.id_condominio = id_condominio
        super().__init__(f"Condominio {id_condominio} no encontrado")
