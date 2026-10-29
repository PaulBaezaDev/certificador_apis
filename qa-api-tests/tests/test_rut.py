"""Suite RUT - bateria de formatos y validacion de RUT (CRITICAL).

En /v1/factura con JWT: si el RUT es valido y != sub -> 403; si es invalido de formato -> 400.
"""
import pytest

from utils import assertions as a
from utils.payloads import factura33, mutate

FE = "/v1/factura"


def _post(client, env, token, p):
    return client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=p)


# rutEmisor: formato del emisor real (10471336-K) en distintas escrituras
FORMATOS_EMISOR = [
    ("RUT-001", "10471336-K", (200, 403)),
    ("RUT-002", "10.471.336-K", (200, 403, 400)),
    ("RUT-003", "10471336K", (200, 403, 400)),
    ("RUT-004", "10471336-k", (200, 403, 400)),
    ("RUT-005", "10.471.336-k", (200, 403, 400)),
]


@pytest.mark.emision
@pytest.mark.parametrize("cid,rut,esperado", FORMATOS_EMISOR, ids=[c[0] for c in FORMATOS_EMISOR])
def test_formatos_rut_emisor(client, env, token, budget, cid, rut, esperado):
    """rutEmisor del emisor real en distintas escrituras: documentar aceptacion."""
    budget.check()
    r = _post(client, env, token, factura33(rutEmisor=rut))
    budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)


RUT_INVALIDOS = [
    ("RUT-006", "10471336-0", (400,)),      # DV incorrecto
    ("RUT-008", "1-9", (400,)),             # muy corto
    ("RUT-009", "123456789012-3", (400,)),  # muy largo
    ("RUT-010", "", (400, 403)),
    ("RUT-012", "10471336", (400, 403)),    # sin DV
    ("RUT-013", "ABCDEFGH-I", (400,)),
    ("RUT-014", " 10471336-K ", (400, 200, 403)),
    ("RUT-015", "10-471-336-K", (400,)),
    ("RUT-016", "1.0471.336-K", (400,)),
    ("RUT-017a", "10471336-K;--", (400,)),
    ("RUT-017b", "<script>", (400,)),
    ("RUT-018", "10471336-±", (400,)),
]


@pytest.mark.emision
@pytest.mark.parametrize("cid,rut,esperado", RUT_INVALIDOS, ids=[c[0] for c in RUT_INVALIDOS])
def test_rut_emisor_invalido(client, env, token, budget, cid, rut, esperado):
    """rutEmisor con formato invalido -> 400 (modulo 11)."""
    budget.check()
    r = _post(client, env, token, factura33(rutEmisor=rut))
    budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)


@pytest.mark.emision
@pytest.mark.case_id("RUT-011")
def test_rut_emisor_null(client, env, token, budget):
    """rutEmisor null -> 400."""
    budget.check()
    r = _post(client, env, token, mutate(factura33(), "rutEmisor", None))
    budget.maybe_record("RUT-011", r, FE)
    a.status_in(r, 400, 403)


@pytest.mark.emision
@pytest.mark.parametrize("cid,rut,esperado", [
    ("RUT-020a", "26461274-0", (400,)),   # DV malo receptor
    ("RUT-020b", "", (400,)),
    ("RUT-020c", "sin-guion", (400,)),
    ("RUT-020d", "12345", (400,)),
])
def test_rut_receptor_invalido(client, env, token, budget, cid, rut, esperado):
    """receptor.rut invalido -> 400."""
    budget.check()
    r = _post(client, env, token, mutate(factura33(), "receptor.rut", rut))
    budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)


@pytest.mark.emision
@pytest.mark.case_id("RUT-021")
def test_caso_critico_jwt_distinto_rutemisor(client, env, token, budget):
    """CRITICO: sub=10471336-K, rutEmisor=77151256-9 (valido, otro) -> 403, NO emite."""
    budget.check()
    r = _post(client, env, token, factura33(rutEmisor="77151256-9"))
    emitido = budget.maybe_record("RUT-021", r, FE)
    a.status_in(r, 403)
    a.codigo_respuesta(r, "403")
    assert not emitido, "DEFECTO GRAVE: emitio DTE con rutEmisor != sub del JWT"


@pytest.mark.emision
@pytest.mark.app
@pytest.mark.case_id("RUT-022")
def test_caso_critico_app_otro_rut(client, env, budget):
    """CRITICO: /v1/app/factura con rutEmisor de otro comercio -> 403 'no habilitado'
    (200 seria hallazgo grave de autorizacion)."""
    budget.check()
    r = client.post(f"{env['base_recepcion']}/v1/app/factura", json_body=factura33(rutEmisor="77151256-9"))
    emitido = budget.maybe_record("RUT-022", r, "/v1/app/factura")
    a.sin_stacktrace(r)
    a.status_in(r, 403, 401, 400)
    assert not emitido, "DEFECTO GRAVE: /v1/app/factura emitio a nombre de otro comercio"
