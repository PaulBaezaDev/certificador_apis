"""Suite F33X - seguridad / Content-Type / metodos HTTP sobre /v1/factura."""
import pytest

from utils import assertions as a
from utils.payloads import factura33
import json as _json

FE = "/v1/factura"


@pytest.mark.seguridad
@pytest.mark.emision
@pytest.mark.parametrize("cid,ct,esperado", [
    ("F33X-001a", "text/plain", (415, 400)),
    ("F33X-001b", "application/xml", (415, 400)),
    ("F33X-002", "multipart/form-data", (415, 400)),
])
def test_content_type_incorrecto(client, env, token, budget, cid, ct, esperado):
    """Content-Type != application/json con body JSON -> 415/400."""
    budget.check()
    r = client.post(f"{env['base_recepcion']}{FE}", token=token,
                    raw_body=_json.dumps(factura33()), headers={"Content-Type": ct})
    budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)


@pytest.mark.seguridad
@pytest.mark.emision
@pytest.mark.case_id("F33X-001c")
def test_sin_content_type(client, env, token, budget):
    """Sin Content-Type -> 415/400 (o 200 si asume json)."""
    budget.check()
    import requests
    r = requests.post(f"{env['base_recepcion']}{FE}",
                      headers={"Authorization": f"Bearer {token}"},
                      data=_json.dumps(factura33()).encode(), timeout=30)
    assert r.status_code in (200, 400, 415), r.status_code


@pytest.mark.emision
@pytest.mark.parametrize("cid,body,esperado", [
    ("F33X-003", "", (400,)),
    ("F33X-004a", "null", (400,)),
    ("F33X-004b", "[]", (400,)),
    ("F33X-004c", '"texto"', (400,)),
    ("F33X-005", '{"rutEmisor":"10471336-K",', (400,)),
])
def test_body_malformado(client, env, token, budget, cid, body, esperado):
    """Body vacio / null / array / JSON roto -> 400."""
    budget.check()
    r = client.post(f"{env['base_recepcion']}{FE}", token=token, raw_body=body)
    budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)


@pytest.mark.parametrize("metodo", ["GET", "PUT", "PATCH", "DELETE", "OPTIONS"])
def test_metodos_no_permitidos(client, env, token, metodo):
    """Metodo != POST sobre /v1/factura -> 405 (verificado GET -> 500, defecto)."""
    r = client.request(metodo, f"{env['base_recepcion']}{FE}", token=token, json_body={})
    a.sin_stacktrace(r)
    a.status_in(r, 405, 204)


@pytest.mark.seguridad
@pytest.mark.emision
@pytest.mark.case_id("F33X-007")
def test_payload_grande_controlado(client, env, token, budget):
    """10 items con nombreItem de 5KB (~55KB) -> 400/413/200 (documentar limite)."""
    budget.check()
    items = [{"numeroLinea": i, "nombreItem": "A" * 5000, "cantidad": 1,
              "precioUnitarioNeto": 1000, "monto": 1000} for i in range(1, 11)]
    p = factura33(items=items, montoNeto=10000, montoIVA=1900, montoTotal=11900)
    r = client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=p)
    budget.maybe_record("F33X-007", r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, 200, 400, 413)


@pytest.mark.seguridad
@pytest.mark.emision
@pytest.mark.case_id("F33X-009")
def test_sqli_en_rutemisor(client, env, token, budget):
    """SQLi en rutEmisor -> 400 (modulo 11), sin error SQL."""
    budget.check()
    p = factura33(rutEmisor="10471336-K' OR '1'='1")
    r = client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=p)
    budget.maybe_record("F33X-009", r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, 400, 403)


@pytest.mark.emision
@pytest.mark.parametrize("cid,path", [
    ("F33X-010a", "/v1//factura"),
    ("F33X-010b", "/V1/FACTURA"),
])
def test_path_variantes(client, env, token, budget, cid, path):
    """Variantes de path (doble slash, mayusculas) -> 404/405, no 200."""
    budget.check()
    r = client.post(f"{env['base_recepcion']}{path}", token=token, json_body=factura33())
    budget.maybe_record(cid, r, FE)
    a.status_in(r, 403, 404, 405)
