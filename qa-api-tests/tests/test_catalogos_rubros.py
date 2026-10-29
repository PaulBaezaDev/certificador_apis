"""Suite RUB - GET /v1/rubros (prioridad HIGH)."""
import pytest

from utils import assertions as a


@pytest.fixture()
def url(env):
    return f"{env['base_recepcion']}/v1/rubros"


@pytest.mark.case_id("RUB-001")
def test_happy(client, token, url):
    """200 con data[] y total."""
    r = client.get(url, token=token)
    a.status_in(r, 200)
    assert r.json["data"] and isinstance(r.json["total"], int)


@pytest.mark.case_id("RUB-002")
def test_schema(client, token, url):
    """Cada rubro {id:int, nombre:str}."""
    for it in client.get(url, token=token).json["data"]:
        assert isinstance(it["id"], int) and isinstance(it["nombre"], str) and it["nombre"].strip()


@pytest.mark.case_id("RUB-003")
def test_total_coincide(client, token, url):
    """total == len(data)."""
    r = client.get(url, token=token)
    assert r.json["total"] == len(r.json["data"])


@pytest.mark.case_id("RUB-004")
def test_ids_unicos(client, token, url):
    """id de rubro sin duplicados."""
    ids = [x["id"] for x in client.get(url, token=token).json["data"]]
    assert len(ids) == len(set(ids))


@pytest.mark.case_id("RUB-006")
def test_21_rubros(client, token, url):
    """QA expone 21 rubros."""
    assert client.get(url, token=token).json["total"] == 21


@pytest.mark.parametrize("metodo", ["POST", "PUT", "DELETE", "PATCH"])
def test_metodos(client, token, url, metodo):
    """Metodo != GET -> 405."""
    r = client.request(metodo, url, token=token, json_body={})
    a.sin_stacktrace(r)
    a.status_in(r, 405)


@pytest.mark.parametrize("caso", ["sin-token", "garbage", "bearer-vacio"])
def test_auth(client, url, caso):
    """Token invalido/ausente -> 401."""
    tok = {"sin-token": None, "garbage": "x.y.z", "bearer-vacio": ""}[caso]
    r = client.get(url, token=tok)
    a.status_in(r, 401, 403)
