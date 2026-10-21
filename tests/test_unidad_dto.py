import pytest
from pydantic import ValidationError

from app.dto.unidad_dto import UnidadActualizar, UnidadCrear


def test_normaliza_torre_piso_numero_a_mayuscula_sin_espacios():
    dto = UnidadCrear(torre=" a ", piso=" 3 ", numero=" 101 ")
    assert dto.torre == "A"
    assert dto.piso == "3"
    assert dto.numero == "101"

def test_torre_vacia_cae_a_unica():
    dto = UnidadCrear(torre="   ", piso="1", numero="1")
    assert dto.torre == "UNICA"

def test_torre_omitida_usa_default_unica():
    dto = UnidadCrear(piso="1", numero="1")
    assert dto.torre == "UNICA"

def test_torre_none_explicito_cae_a_unica():
    dto = UnidadCrear(torre=None, piso="1", numero="1")
    assert dto.torre == "UNICA"

def test_actualizar_normaliza_torre_a_mayuscula_sin_espacios():
    dto = UnidadActualizar(torre=" b ")
    assert dto.torre == "B"

def test_actualizar_torre_none_explicito_se_mantiene_none():
    dto = UnidadActualizar(torre=None)
    assert dto.torre is None

def test_torre_no_string_falla_422_en_vez_de_500():
    with pytest.raises(ValidationError):
        UnidadCrear(torre=5, piso="1", numero="1")

def test_actualizar_torre_no_string_falla_422_en_vez_de_500():
    with pytest.raises(ValidationError):
        UnidadActualizar(torre=["a"])

def test_piso_vacio_no_cae_a_unica_sino_que_falla_422():
    with pytest.raises(ValidationError):
        UnidadCrear(torre="A", piso="   ", numero="1")

def test_numero_vacio_no_cae_a_unica_sino_que_falla_422():
    with pytest.raises(ValidationError):
        UnidadCrear(torre="A", piso="1", numero="   ")

def test_actualizar_normaliza_solo_campos_enviados():
    dto = UnidadActualizar(numero=" 205b ")
    assert dto.numero == "205B"
    assert dto.torre is None

def test_actualizar_piso_vacio_falla_422():
    with pytest.raises(ValidationError):
        UnidadActualizar(piso="   ")
