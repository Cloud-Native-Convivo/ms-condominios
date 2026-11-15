from fastapi import Request
from fastapi.responses import JSONResponse

from app.exception.condominio_exception import (
    CondominioConUnidadesException,
    CondominioNoEncontradoException,
)
from app.exception.unidad_exception import (
    UnidadDuplicadaException,
    UnidadIncompatibleConTipoException,
    UnidadInexistenteException,
    UnidadNoEncontradaException,
)


def condominio_no_encontrado_handler(_request: Request, exc: CondominioNoEncontradoException):
    return JSONResponse(status_code=404, content={"message": str(exc)})


def condominio_con_unidades_handler(_request: Request, exc: CondominioConUnidadesException):
    return JSONResponse(status_code=409, content={"message": str(exc)})


def unidad_invalida_handler(
    _request: Request, exc: UnidadIncompatibleConTipoException | UnidadInexistenteException
):
    return JSONResponse(status_code=422, content={"message": str(exc)})


def unidad_no_encontrada_handler(_request: Request, exc: UnidadNoEncontradaException):
    return JSONResponse(status_code=404, content={"message": str(exc)})


def unidad_duplicada_handler(_request: Request, exc: UnidadDuplicadaException):
    return JSONResponse(status_code=409, content={"message": str(exc)})
