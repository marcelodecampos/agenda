import importlib.util
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "importar_localidades_ibge",
    Path(__file__).parents[1] / "scripts" / "importar_localidades_ibge.py",
)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
_decimal = _MODULE._decimal
_valor = _MODULE._valor


def test_valor_aceita_aliases_do_mdb_e_shape() -> None:
    propriedades = {"CD_GEOCODI": "355030800000001", "NM_LOCALID": "Centro"}

    assert _valor(propriedades, "CD_GEOCODIGO", "CD_GEOCODI") == "355030800000001"
    assert _valor(propriedades, "NM_LOCALIDADE", "NM_LOCALID") == "Centro"


def test_decimal_normaliza_valor_com_virgula() -> None:
    assert _decimal("-46,633309") == -46.633309
    assert _decimal(None) is None