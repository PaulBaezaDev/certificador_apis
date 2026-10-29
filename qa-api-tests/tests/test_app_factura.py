"""Suite APPF - emision canal App/POS /v1/app/factura (MEDIUM). Segun doc: sin JWT."""
import pytest

from utils import assertions as a
from utils.payloads import factura33, factura34

AF = "/v1/app/factura"


@pytest.mark.app
@pytest.mark.emision
@pytest.mark.case_id("APPF-001")
def test_app_factura33_sin_token(client, env, budget):
    """Doc: /v1/app/factura sin token emite (200). Verificado gateway -> 401 (posible defecto H-03)."""
    budget.check()
    r = client.post(f"{env['base_recepcion']}{AF}", json_body=factura33())
    budget.maybe_record("APPF-001", r, AF)
    a.sin_stacktrace(r)
    a.status_in(r, 200)  # contrato manual v1.5 seccion 7


@pytest.mark.app
@pytest.mark.emision
@pytest.mark.case_id("APPF-002")
def test_app_factura33_con_token(client, env, token, budget):
    """/v1/app/factura con Bearer -> 200 o 401 (documentar)."""
    budget.check()
    r = client.post(f"{env['base_recepcion']}{AF}", token=token, json_body=factura33())
    budget.maybe_record("APPF-002", r, AF)
    a.sin_stacktrace(r)
    a.status_in(r, 200, 401)


@pytest.mark.app
@pytest.mark.parametrize("cid,payload,esperado", [
    ("APPF-004", factura33(rutEmisor="10471336-1"), (400,)),        # DV malo
    ("APPF-005", {k: v for k, v in factura33().items() if k != "rutEmisor"}, (400,)),
])
def test_app_factura_validaciones(client, env, cid, payload, esperado):
    """Validaciones basicas del canal app (rutEmisor modulo 11 / obligatorio)."""
    r = client.post(f"{env['base_recepcion']}{AF}", json_body=payload)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado, 401)


@pytest.mark.app
@pytest.mark.emision
@pytest.mark.case_id("APPF-006")
def test_app_factura34(client, env, budget):
    """/v1/app/factura tipo 34 -> 200 / 401."""
    budget.check()
    r = client.post(f"{env['base_recepcion']}{AF}", json_body=factura34())
    budget.maybe_record("APPF-006", r, AF)
    a.status_in(r, 200, 401)


@pytest.mark.app
@pytest.mark.parametrize("metodo", ["GET", "PUT", "DELETE"])
def test_app_factura_metodos(client, env, metodo):
    """Metodo != POST -> 405."""
    r = client.request(metodo, f"{env['base_recepcion']}{AF}", json_body={})
    a.sin_stacktrace(r)
    a.status_in(r, 405, 401)


@pytest.mark.app
@pytest.mark.emision
@pytest.mark.seguridad
@pytest.mark.case_id("APPF-009")
def test_app_factura_autorizacion_cruzada(client, env, budget):
    """CLAVE: sin validacion sub, ¿se puede emitir a nombre de cualquier comercio habilitado?
    Se prueba con el emisor real (77151256-9 del manual) - si emite = hallazgo de autorizacion."""
    budget.check()
    r = client.post(f"{env['base_recepcion']}{AF}", json_body=factura33(rutEmisor="77151256-9"))
    emitido = budget.maybe_record("APPF-009", r, AF)
    a.sin_stacktrace(r)
    if emitido:
        pytest.fail("HALLAZGO: /v1/app/factura permite emitir a nombre de otro comercio sin prueba de identidad")
    a.status_in(r, 400, 401, 403)
