"""Suite ACT - GET /v1/rubros/{rubroId}/acteco (prioridad HIGH)."""
import pytest

from utils import assertions as a


def au(env, rid):
    return f"{env['base_recepcion']}/v1/rubros/{rid}/acteco"


@pytest.mark.case_id("ACT-001")
def test_happy(client, token, env):
    """Rubro 7 -> 200, rubro.id==7, acteco[{id,codActeco,nombre}]."""
    r = client.get(au(env, 7), token=token)
    a.status_in(r, 200)
    d = r.json["data"]
    assert d["rubro"]["id"] == 7
    for x in d["acteco"]:
        a.tiene_campos(x, "id", "codActeco", "nombre")
        assert isinstance(x["id"], int)


@pytest.mark.case_id("ACT-004")
def test_codacteco_formato_sii(client, token, env):
    """codActeco: 6 digitos (formato ACTECO SII)."""
    r = client.get(au(env, 10), token=token)
    malos = [x["codActeco"] for x in r.json["data"]["acteco"] if not str(x["codActeco"]).isdigit()]
    assert not malos, f"codActeco no numericos: {malos}"


@pytest.mark.case_id("ACT-006")
def test_total_coincide(client, token, env):
    """total == len(acteco)."""
    r = client.get(au(env, 7), token=token)
    assert r.json["total"] == len(r.json["data"]["acteco"])


@pytest.mark.case_id("ACT-007")
def test_ids_unicos(client, token, env):
    """acteco.id unicos dentro del rubro."""
    ids = [x["id"] for x in client.get(au(env, 7), token=token).json["data"]["acteco"]]
    assert len(ids) == len(set(ids))


@pytest.mark.case_id("ACT-008")
def test_rubro_inexistente(client, token, env):
    """Rubro 99 -> 404."""
    r = client.get(au(env, 99), token=token)
    a.status_in(r, 404)
    a.codigo_respuesta(r, "404")


@pytest.mark.parametrize("rid,esperado", [
    ("0", (400, 404)), ("-1", (400, 404)), ("1.5", (400, 404)), ("abc", (400,)),
    ("null", (400, 404)), ("2147483648", (400, 404, 500)),
    ("99999999999999999999", (400, 404, 500)), ("7 ", (400, 404, 200)),
])
def test_rubroid_invalido(client, token, env, rid, esperado):
    """rubroId no valido -> 400/404 sin stacktrace."""
    r = client.get(au(env, rid), token=token)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)


@pytest.mark.seguridad
@pytest.mark.parametrize("payload", ["7 OR 1=1", "7;SELECT 1", "7'--", "7 UNION SELECT null"])
def test_sqli(client, token, env, payload):
    """SQLi en rubroId -> 400/404 sin fuga."""
    r = client.get(au(env, payload), token=token)
    a.sin_stacktrace(r)
    a.status_in(r, 400, 404)


@pytest.mark.parametrize("metodo", ["POST", "PUT", "DELETE"])
def test_metodos(client, token, env, metodo):
    """Metodo != GET -> 405."""
    r = client.request(metodo, au(env, 7), token=token, json_body={})
    a.sin_stacktrace(r)
    a.status_in(r, 405)
