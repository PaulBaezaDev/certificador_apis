"""Suite AUTH - autenticacion / autorizacion (CRITICAL/HIGH).

Nota: el servicio de login limita el numero de tokens activos por usuario
(code 88 'Maximo de tokens excedido'). Todas las variantes se derivan de UN token
de sesion, sin logins adicionales.
"""
import pytest

from utils import assertions as a
from utils.auth import (tamper_payload, bad_signature, malformed_two_segments,
                        garbage_token, huge_token, expired_token)
from utils.payloads import factura33


@pytest.fixture()
def reg_url(env):
    return f"{env['base_recepcion']}/v1/regiones"


@pytest.mark.case_id("AUTH-001")
def test_token_valido(client, token, reg_url):
    """Token valido y vigente -> 200."""
    a.status_in(client.get(reg_url, token=token), 200)


@pytest.mark.parametrize("caso,header", [
    ("AUTH-002-sin-header", None),
    ("AUTH-003-header-vacio", {"Authorization": ""}),
    ("AUTH-004-basic", {"Authorization": "Basic dXNlcjpwYXNz"}),
    ("AUTH-005-esquema-token", {"Authorization": "Token abc.def.ghi"}),
    ("AUTH-006-bearer-sin-token", {"Authorization": "Bearer "}),
    ("AUTH-014-token-con-espacios", {"Authorization": "Bearer ey J0 eXA"}),
])
def test_headers_invalidos(client, reg_url, caso, header):
    """Header Authorization invalido -> 401."""
    r = client.get(reg_url, headers=header)
    a.sin_stacktrace(r)
    a.status_in(r, 401, 403)


@pytest.mark.case_id("AUTH-007")
def test_bearer_minusculas(client, token, reg_url):
    """Esquema 'bearer' en minusculas: documentar 200 vs 401."""
    r = client.get(reg_url, headers={"Authorization": f"bearer {token}"})
    a.sin_stacktrace(r)
    a.status_in(r, 200, 401)


@pytest.mark.parametrize("caso,mut", [
    ("AUTH-008-malformado", malformed_two_segments),
    ("AUTH-009-firma-alterada", bad_signature),
    ("AUTH-010-expirado", expired_token),
    ("AUTH-011-sub-vacio", lambda t: tamper_payload(t, sub="")),
    ("AUTH-011b-sin-sub", lambda t: tamper_payload(t, sub=None)),
])
def test_token_manipulado(client, token, reg_url, caso, mut):
    """Token manipulado -> 401/403. La app NO valida firma/exp (manual 12.2):
    se documenta si el gateway lo bloquea o pasa."""
    r = client.get(reg_url, token=mut(token))
    a.sin_stacktrace(r)
    a.status_in(r, 401, 403)


@pytest.mark.case_id("AUTH-013")
def test_doble_bearer(client, token, reg_url):
    """Dos valores en Authorization -> comportamiento definido (no 500)."""
    import requests
    s = requests.Session()
    r = s.get(reg_url, headers=[("Authorization", f"Bearer {token}"),
                                ("Authorization", "Bearer otro")])
    assert r.status_code != 500


@pytest.mark.case_id("AUTH-015")
def test_token_gigante(client, reg_url):
    """Token de 100KB -> 401/431, no 500."""
    r = client.get(reg_url, token=huge_token())
    a.status_in(r, 401, 403, 431, 414)


@pytest.mark.case_id("AUTH-022")
@pytest.mark.seguridad
def test_actuator_con_bearer(client, token, env):
    """actuator/health con Bearer: manual dice que requiere Bearer;
    verificado -> 403 SigV4 (fuga de info de infraestructura)."""
    r = client.get("https://apiqa-cloud.mcdesaqa.cl/mcs-central-be-recepcion-fe/actuator/health",
                   token=token)
    a.status_in(r, 200)  # contrato manual 13


# ---- autorizacion: sub vs rutEmisor (usa payload que igual fallaria validacion) ----

@pytest.mark.emision
@pytest.mark.case_id("AUTH-019")
def test_sub_distinto_rutemisor(client, token, env, budget):
    """sub(10471336-K) != rutEmisor(77151256-9) -> 403 codigoRespuesta 403, NO emite."""
    budget.check()
    p = factura33(rutEmisor="77151256-9")
    r = client.post(f"{env['base_recepcion']}/v1/factura", token=token, json_body=p)
    budget.maybe_record("AUTH-019", r, "/v1/factura")
    a.status_in(r, 403)
    a.codigo_respuesta(r, "403")


@pytest.mark.emision
@pytest.mark.case_id("AUTH-020")
def test_sub_igual_pero_payload_invalido(client, token, env, budget):
    """sub == rutEmisor con payload invalido -> 400 (no 403)."""
    budget.check()
    p = factura33(montoTotal=None, montoNeto=None, montoIVA=None, items=[])
    r = client.post(f"{env['base_recepcion']}/v1/factura", token=token, json_body=p)
    budget.maybe_record("AUTH-020", r, "/v1/factura")
    a.status_in(r, 400)


@pytest.mark.nc
@pytest.mark.emision
@pytest.mark.case_id("AUTH-021")
def test_nc_sub_distinto(client, token, env, budget):
    """NC con sub != rutEmisor -> 403."""
    budget.check()
    from utils.payloads import nota_credito
    p = nota_credito(1, rutEmisor="77151256-9")
    r = client.post(f"{env['base_nc']}/v1/nota-credito", token=token, json_body=p)
    a.status_in(r, 403)
