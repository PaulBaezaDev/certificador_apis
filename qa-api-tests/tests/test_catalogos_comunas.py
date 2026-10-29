"""Suite COM - GET /v1/regiones/{regionId}/comunas (prioridad HIGH)."""
import pytest

from utils import assertions as a


def cu(env, rid):
    return f"{env['base_recepcion']}/v1/regiones/{rid}/comunas"


@pytest.mark.case_id("COM-001")
def test_happy_rm(client, token, env):
    """Region 13 -> 200, region.id==13, comunas[]."""
    r = client.get(cu(env, 13), token=token)
    a.status_in(r, 200)
    d = r.json["data"]
    assert d["region"]["id"] == 13
    assert isinstance(d["comunas"], list) and d["comunas"]


@pytest.mark.case_id("COM-003")
def test_schema(client, token, env):
    """Schema data.region{id,nombre} + comunas[{id,nombre}] + total."""
    r = client.get(cu(env, 4), token=token)
    d = r.json["data"]
    a.tiene_campos(d, "region", "comunas")
    a.tiene_campos(d["region"], "id", "nombre")
    for c in d["comunas"]:
        assert isinstance(c["id"], int) and isinstance(c["nombre"], str)


@pytest.mark.case_id("COM-005")
def test_integridad_region_comuna(client, token, env):
    """Toda comuna de la region 13 tiene id con prefijo 13xxx."""
    r = client.get(cu(env, 13), token=token)
    malas = [c for c in r.json["data"]["comunas"] if not str(c["id"]).startswith("13")]
    assert not malas, f"comunas que no pertenecen a la region 13: {malas}"


@pytest.mark.case_id("COM-006")
def test_total_coincide(client, token, env):
    """total == len(comunas)."""
    r = client.get(cu(env, 13), token=token)
    assert r.json["total"] == len(r.json["data"]["comunas"])


@pytest.mark.case_id("COM-007")
def test_ids_unicos(client, token, env):
    """id de comuna sin duplicados dentro de la region."""
    ids = [c["id"] for c in client.get(cu(env, 13), token=token).json["data"]["comunas"]]
    assert len(ids) == len(set(ids))


@pytest.mark.case_id("COM-008")
def test_region_inexistente(client, token, env):
    """Region 99 -> 404."""
    r = client.get(cu(env, 99), token=token)
    a.status_in(r, 404)
    a.codigo_respuesta(r, "404")


@pytest.mark.parametrize("rid,ids,esperado", [
    ("COM-009", "0", (400, 404)),
    ("COM-010", "-1", (400, 404)),
    ("COM-011", "1.5", (400, 404)),
    ("COM-012", "abc", (400,)),
    ("COM-014", "null", (400, 404)),
    ("COM-015", "99999999999999999999", (400, 404, 500)),
    ("COM-016a", "32768", (400, 404)),
    ("COM-016b", "2147483648", (400, 404, 500)),
    ("COM-017a", "13%20", (400, 404)),
    ("COM-017b", "13abc", (400, 404)),
    ("COM-020", "%31%33", (200, 400, 404)),
])
def test_regionid_invalido(client, token, env, rid, ids, esperado):
    """regionId no valido -> 400/404, sin stacktrace."""
    r = client.get(cu(env, ids), token=token)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)


@pytest.mark.seguridad
@pytest.mark.parametrize("payload", [
    "13 OR 1=1", "13;SELECT 1", "13'--", "13) OR ('1'='1", "13 UNION SELECT null",
])
def test_sqli_basica(client, token, env, payload):
    """SQLi en regionId -> 400/404, sin error SQL ni datos filtrados."""
    r = client.get(cu(env, payload), token=token)
    a.sin_stacktrace(r)
    a.status_in(r, 400, 404)


@pytest.mark.seguridad
@pytest.mark.parametrize("payload", ["../rubros", "%2e%2e%2f", "..%2f..%2f"])
def test_path_traversal(client, token, env, payload):
    """Path traversal en regionId -> 400/404."""
    r = client.get(cu(env, payload), token=token)
    a.sin_stacktrace(r)
    a.status_in(r, 400, 404)


@pytest.mark.parametrize("metodo", ["POST", "PUT", "DELETE"])
def test_metodos(client, token, env, metodo):
    """Metodo != GET -> 405."""
    r = client.request(metodo, cu(env, 13), token=token, json_body={})
    a.sin_stacktrace(r)
    a.status_in(r, 405)


@pytest.mark.parametrize("caso", ["sin-token", "garbage"])
def test_auth(client, env, caso):
    """Sin/con token invalido -> 401."""
    tok = None if caso == "sin-token" else "garbage.token.x"
    r = client.get(cu(env, 13), token=tok)
    a.status_in(r, 401, 403)
