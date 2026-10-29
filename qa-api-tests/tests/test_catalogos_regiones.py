"""Suite REG - GET /v1/regiones (prioridad HIGH)."""
import pytest

from utils import assertions as a
from utils.auth import get_token, tamper_payload, bad_signature, malformed_two_segments, garbage_token


@pytest.fixture()
def url(env):
    return f"{env['base_recepcion']}/v1/regiones"


@pytest.mark.case_id("REG-001")
def test_happy(client, token, url):
    """Happy path: 200 con data[] y total."""
    r = client.get(url, token=token)
    a.status_in(r, 200)
    a.is_json_object(r)
    assert isinstance(r.json.get("data"), list) and r.json["data"], "data vacia"
    assert isinstance(r.json.get("total"), int)


@pytest.mark.case_id("REG-002")
def test_schema(client, token, url):
    """Cada region {id:int, nombre:str no vacio}."""
    r = client.get(url, token=token)
    for it in r.json["data"]:
        assert isinstance(it["id"], int)
        assert isinstance(it["nombre"], str) and it["nombre"].strip()


@pytest.mark.case_id("REG-003")
def test_total_coincide(client, token, url):
    """total == len(data)."""
    r = client.get(url, token=token)
    assert r.json["total"] == len(r.json["data"]), "total no coincide con len(data)"


@pytest.mark.case_id("REG-004")
def test_ids_unicos(client, token, url):
    """id de region sin duplicados."""
    ids = [x["id"] for x in client.get(url, token=token).json["data"]]
    assert len(ids) == len(set(ids)), f"ids duplicados: {ids}"


@pytest.mark.case_id("REG-006")
def test_16_regiones(client, token, url):
    """Chile tiene 16 regiones."""
    assert client.get(url, token=token).json["total"] == 16


@pytest.mark.parametrize("metodo", ["POST", "PUT", "DELETE", "PATCH"])
def test_metodos_no_permitidos(client, token, url, metodo):
    """Metodo distinto de GET -> 405 (documentar si 500)."""
    r = client.request(metodo, url, token=token, json_body={})
    a.sin_stacktrace(r)
    a.status_in(r, 405)  # contrato: Method Not Allowed


@pytest.mark.case_id("REG-011")
def test_query_params_basura(client, token, url):
    """Query params no reconocidos se ignoran, 200."""
    r = client.get(url, token=token, params={"x": "1", "drop": "table"})
    a.status_in(r, 200)


@pytest.mark.parametrize("caso,mutador", [
    ("REG-012-sin-token", lambda t: None),
    ("REG-013-garbage", lambda t: garbage_token()),
    ("REG-014-malformado", lambda t: malformed_two_segments(t)),
    ("REG-015-firma-mala", lambda t: bad_signature(t)),
    ("REG-016-sub-vacio", lambda t: tamper_payload(t, sub="")),
])
def test_auth_bateria(client, token, url, caso, mutador):
    """Token invalido -> 401 (o documentar si el gateway/app lo deja pasar)."""
    tok = mutador(token)
    r = client.get(url, token=tok)
    a.status_in(r, 401, 403)
    a.sin_stacktrace(r)
