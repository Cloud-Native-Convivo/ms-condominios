import pytest
from fastapi import HTTPException

from app.config.security_config import (
    UsuarioContexto,
    normalizar_roles,
    obtener_contexto_usuario,
    requerir_roles,
    requerir_roles_contexto,
    requiere_roles,
)


def test_normalizar_roles_condominios():
    assert "admin" in normalizar_roles("ADMIN")
    assert "administrador" in normalizar_roles("admin")
    assert "residente" in normalizar_roles("RESIDENTE")
    assert "admin" in normalizar_roles("administrador")

def test_usuario_contexto_helpers_condominios():
    ctx = UsuarioContexto(usuario_sub="admin-sub", roles={"admin", "administrador"})
    assert ctx.es_admin() is True
    assert ctx.es_residente() is False
    assert ctx.tiene_rol("ADMIN") is True

def test_obtener_contexto_usuario_condominios_sin_sub_retorna_401():
    with pytest.raises(HTTPException) as exc:
        obtener_contexto_usuario(x_usuario_sub="")
    assert exc.value.status_code == 401
    assert "faltante o inválido" in exc.value.detail

def test_obtener_contexto_usuario_condominios_espacios_retorna_401():
    with pytest.raises(HTTPException) as exc:
        obtener_contexto_usuario(x_usuario_sub="   ")
    assert exc.value.status_code == 401

def test_requiere_roles_compatibilidad_alias():
    verificador = requiere_roles(["ADMIN"])
    roles = verificador(x_usuario_roles="administrador")
    assert "admin" in roles or "administrador" in roles

def test_requiere_roles_rechaza_residente_con_403():
    verificador = requiere_roles(["ADMIN"])
    with pytest.raises(HTTPException) as exc:
        verificador(x_usuario_roles="RESIDENTE")
    assert exc.value.status_code == 403
    assert exc.value.detail == "Permisos insuficientes"

def test_requerir_roles_valida_con_usuario_contexto():
    verificador = requerir_roles_contexto(["ADMIN"])
    ctx_res = UsuarioContexto(usuario_sub="u-1", roles={"residente"})
    with pytest.raises(HTTPException) as exc:
        verificador(contexto=ctx_res)
    assert exc.value.status_code == 403
