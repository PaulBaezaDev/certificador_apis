"""Suite DUM - contrato de las APIs mock (devtunnel). Solo corre con ENV=DUMMYS.
Sirve para detectar rapido cuando el colega cambia el mock (ej. la consulta paso a exigir rutEmisor)."""
import pytest

from utils import assertions as a
from utils.payloads import nota_credito

pytestmark = pytest.mark.dummys


@pytest.mark.case_id("DUM-001")
def test_health_up(client, env):
    """actuator/health -> 200 con status UP."""
    r = client.get(env["health"])
    a.status_in(r, 200)
    assert r.json.get("status") == "UP", r.text[:300]


@pytest.mark.case_id("DUM-002")
def test_consulta_post_con_rut(client, env):
    """Consulta DTE en el mock es POST con body {rutEmisor} -> 200 codigoRespuesta 01."""
    r = client.post(f"{env['base_consultas']}/v1/app/dte/33/107", json_body={"rutEmisor": env["user"]})
    a.sin_stacktrace(r)
    a.status_in(r, 200)
    a.codigo_respuesta(r, "01")


@pytest.mark.case_id("DUM-003")
def test_consulta_post_sin_rut(client, env):
    """Consulta sin rutEmisor -> 400 (validacion del mock)."""
    r = client.post(f"{env['base_consultas']}/v1/app/dte/33/107", json_body={})
    a.status_in(r, 400)


@pytest.mark.case_id("DUM-004")
def test_consulta_get_no_existe(client, env):
    """Diferencia conocida con el backend real: GET no esta implementado en el mock -> 404."""
    r = client.get(f"{env['base_consultas']}/v1/app/dte/33/107")
    a.status_in(r, 404)


@pytest.mark.case_id("DUM-005")
def test_nota_credito_app(client, env):
    """/v1/app/nota-credito con payload completo -> 2xx (el mock responde 201)."""
    r = client.post(f"{env['base_nc']}/v1/app/nota-credito", json_body=nota_credito(107))
    a.sin_stacktrace(r)
    a.status_in(r, 200, 201)


@pytest.mark.case_id("DUM-006")
def test_nota_credito_app_vacia(client, env):
    """/v1/app/nota-credito con body vacio -> 400."""
    r = client.post(f"{env['base_nc']}/v1/app/nota-credito", json_body={})
    a.status_in(r, 400)
