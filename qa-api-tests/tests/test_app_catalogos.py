"""Suite APPC - catalogos canal App/POS /v1/app/* (segun doc: sin JWT). Prioridad MEDIUM/HIGH."""
import pytest

from utils import assertions as a


@pytest.mark.app
@pytest.mark.case_id("APPC-001")
def test_regiones_sin_token(client, env):
    """Doc: /v1/app/regiones sin token -> 200. Verificar comportamiento real."""
    r = client.get(f"{env['base_recepcion']}/v1/app/regiones")
    a.sin_stacktrace(r)
    a.status_in(r, 200)  # contrato manual v1.5 seccion 7


@pytest.mark.app
@pytest.mark.case_id("APPC-002")
def test_regiones_con_token(client, token, env):
    """/v1/app/regiones con Bearer valido."""
    r = client.get(f"{env['base_recepcion']}/v1/app/regiones", token=token)
    a.sin_stacktrace(r)
    a.status_in(r, 200, 401)


@pytest.mark.app
@pytest.mark.parametrize("path", [
    "/v1/app/regiones/13/comunas", "/v1/app/rubros", "/v1/app/rubros/7/acteco",
])
def test_resto_catalogos_sin_token(client, env, path):
    """Doc: catalogos /v1/app/* accesibles sin JWT -> 200."""
    r = client.get(f"{env['base_recepcion']}{path}")
    a.sin_stacktrace(r)
    a.status_in(r, 200)


@pytest.mark.app
@pytest.mark.case_id("APPC-009")
def test_app_vs_jwt_mismo_payload(client, token, env):
    """data de /v1/app/regiones == data de /v1/regiones."""
    con = client.get(f"{env['base_recepcion']}/v1/regiones", token=token)
    sin = client.get(f"{env['base_recepcion']}/v1/app/regiones")
    if sin.status != 200 or con.status != 200:
        pytest.skip(f"no comparable: app={sin.status} jwt={con.status}")
    assert con.json["data"] == sin.json["data"]


@pytest.mark.app
@pytest.mark.parametrize("path,esperado", [
    ("/v1/app/regiones/99/comunas", (404,)),
    ("/v1/app/regiones/abc/comunas", (400,)),
    ("/v1/app/rubros/99/acteco", (404,)),
    ("/v1/app/rubros/-1/acteco", (400, 404)),
])
def test_app_params_invalidos(client, env, path, esperado):
    """params invalidos en catalogos app -> 400/404 (si el canal responde)."""
    r = client.get(f"{env['base_recepcion']}{path}")
    a.sin_stacktrace(r)
    a.status_in(r, *esperado, 401)
