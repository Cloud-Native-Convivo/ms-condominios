from fastapi import Request
from fastapi.responses import JSONResponse
from app.exception.condominio_exception import CondominioNoEncontradoException

def condominio_no_encontrado_handler(_request: Request, exc: CondominioNoEncontradoException):
    return JSONResponse(status_code=404, content={"message": str(exc)})
