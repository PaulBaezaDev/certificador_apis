"""Suite NC - Nota de Credito tipo 61 (CRITICAL). Servicio recepcion-nc / v1/nota-credito.

El happy path requiere una factura ACEPTADA por el SII (asincrono). Si no se logra,
NC-002/003/011/018 quedan BLOCKED y se documenta la respuesta real.
"""
import time

import pytest

from utils import assertions as a
from utils.payloads import factura33, nota_credito, mutate

FEC = "/v1/factura"
NCE = "/v1/nota-credito"


@pytest.fixture(scope="module")
def factura_referenciable(env, token, budget):
    """Emite una factura 33 y espera (breve) a que quede ACEPTADA. Devuelve (folio, estado)."""
    from utils.api_client import ApiClient
    c = ApiClient()
    budget.check()
    r = c.post(f"{env['base_recepcion']}{FEC}", token=token, json_body=factura33())
    budget.maybe_record("NC-fixture-emit", r, FEC)
    if not (r.status == 200 and r.codigo_respuesta == "01"):
        pytest.skip(f"no se pudo emitir factura para NC: {r.status} {r.text[:150]}")
    folio = r.json["datosDTE"]["folio"]
    estado = None
    for _ in range(6):
        q = c.post(f"{env['base_consultas']}/v1/app/dte/33/{folio}", token=token, json_body={"rutEmisor": env["user"]})
        if q.status == 200:
            estado = q.json["datosFactura"].get("estado")
            if estado == "ACEPTADO":
                break
        time.sleep(5)
    return {"folio": folio, "estado": estado}


@pytest.mark.nc
@pytest.mark.emision
@pytest.mark.case_id("NC-001")
def test_tipo61_en_endpoint_factura(client, env, token, budget):
    """tipoDte 61 enviado a /v1/factura -> 400 (endpoint no soporta 61)."""
    budget.check()
    r = client.post(f"{env['base_recepcion']}{FEC}", token=token, json_body=factura33(tipoDte=61))
    budget.maybe_record("NC-001", r, FEC)
    a.sin_stacktrace(r)
    a.status_in(r, 400)


@pytest.mark.nc
@pytest.mark.emision
@pytest.mark.bloqueante
@pytest.mark.case_id("NC-002")
def test_nc_happy_anulacion(client, env, token, budget, factura_referenciable):
    """Anulacion (codigoReferencia 1) de factura ACEPTADA -> 200 tipoDte 61 + folio."""
    if factura_referenciable["estado"] != "ACEPTADO":
        pytest.skip(f"factura {factura_referenciable['folio']} en estado "
                    f"{factura_referenciable['estado']} (no ACEPTADO) - NC happy no ejecutable")
    budget.check()
    p = nota_credito(factura_referenciable["folio"])
    r = client.post(f"{env['base_nc']}{NCE}", token=token, json_body=p)
    budget.maybe_record("NC-002", r, NCE)
    a.status_in(r, 200)
    a.codigo_respuesta(r, "01")
    assert r.json["datosDTE"]["tipoDte"] == 61


@pytest.mark.nc
@pytest.mark.emision
@pytest.mark.bloqueante
@pytest.mark.case_id("NC-018")
def test_nc_duplicada(client, env, token, budget, factura_referenciable):
    """2a NC sobre la misma factura -> 409 codigoRespuesta 97 / 422."""
    if factura_referenciable["estado"] != "ACEPTADO":
        pytest.skip("requiere factura ACEPTADO")
    p = nota_credito(factura_referenciable["folio"])
    client.post(f"{env['base_nc']}{NCE}", token=token, json_body=p)
    r = client.post(f"{env['base_nc']}{NCE}", token=token, json_body=p)
    a.status_in(r, 409, 422)


@pytest.mark.nc
@pytest.mark.case_id("NC-023")
def test_nc_factura_no_aceptada(client, env, token, factura_referenciable):
    """Factura recien emitida (no ACEPTADO) -> 422 FACTURA_NO_ACEPTADA_SII."""
    if factura_referenciable["estado"] == "ACEPTADO":
        pytest.skip("la factura quedo ACEPTADO; caso no aplica")
    p = nota_credito(factura_referenciable["folio"])
    r = client.post(f"{env['base_nc']}{NCE}", token=token, json_body=p)
    a.sin_stacktrace(r)
    a.status_in(r, 422, 400)


@pytest.mark.nc
@pytest.mark.parametrize("cid,folio,esperado", [
    ("NC-005", 999999999, (422, 404, 400)),
    ("NC-007a", 0, (400,)),
    ("NC-007b", -1, (400,)),
])
def test_nc_folio_referencia(client, env, token, cid, folio, esperado):
    """datosFactura.folio invalido/inexistente -> 400/404/422."""
    p = nota_credito(folio)
    r = client.post(f"{env['base_nc']}{NCE}", token=token, json_body=p)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)


@pytest.mark.nc
@pytest.mark.parametrize("cid,path,valor,esperado", [
    ("NC-006a", "datosFactura.tipoDte", 99, (400,)),
    ("NC-006b", "datosFactura.tipoDte", 61, (400,)),
    ("NC-007c", "datosFactura.folio", "abc", (400,)),
    ("NC-007d", "datosFactura.folio", 1.5, (400,)),
    ("NC-010", "datosFactura.montoTotal", 999_999_999, (400, 422)),
    ("NC-012", "datosFactura.montoTotal", 0, (400,)),
    ("NC-013", "datosFactura.montoTotal", -119000, (400,)),
    ("NC-014a", "codigoReferencia", 0, (400,)),
    ("NC-014b", "codigoReferencia", 2, (400, 422)),
    ("NC-014c", "codigoReferencia", 99, (400, 422)),
    ("NC-014d", "codigoReferencia", "1", (400,)),
    ("NC-016", "razonReferencia", "X" * 91, (400,)),
    ("NC-017", "razonReferencia", "X" * 5000, (400,)),
])
def test_nc_validaciones(client, env, token, cid, path, valor, esperado):
    """Validaciones de payload NC -> 400/422."""
    p = mutate(nota_credito(12345), path, valor)
    r = client.post(f"{env['base_nc']}{NCE}", token=token, json_body=p)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)


@pytest.mark.nc
@pytest.mark.parametrize("cid,mut", [
    ("NC-019a", lambda p: {k: v for k, v in p.items() if k != "codigoReferencia"}),
    ("NC-019b", lambda p: {k: v for k, v in p.items() if k != "rutEmisor"}),
    ("NC-019c", lambda p: {k: v for k, v in p.items() if k != "receptor"}),
    ("NC-019d", lambda p: {k: v for k, v in p.items() if k != "datosFactura"}),
])
def test_nc_obligatorios(client, env, token, cid, mut):
    """Campos obligatorios NC omitidos -> 400."""
    r = client.post(f"{env['base_nc']}{NCE}", token=token, json_body=mut(nota_credito(12345)))
    a.status_in(r, 400, 403)


@pytest.mark.nc
@pytest.mark.case_id("NC-008")
def test_nc_factura_otro_emisor(client, env, token, factura_referenciable):
    """Referenciar factura de otro emisor -> 403/422, sin revelar datos."""
    p = nota_credito(factura_referenciable["folio"])
    p["rutEmisor"] = "10471336-K"
    p["datosFactura"]["folio"] = 1  # folio que probablemente no es de este emisor
    r = client.post(f"{env['base_nc']}{NCE}", token=token, json_body=p)
    a.sin_stacktrace(r)
    a.status_in(r, 403, 422, 404, 400)


@pytest.mark.nc
@pytest.mark.parametrize("cid,tok,esperado", [
    ("NC-021a", None, (401,)),
    ("NC-021b", "garbage.tok.x", (401, 403)),
])
def test_nc_auth(client, env, cid, tok, esperado):
    """NC sin token / token invalido -> 401/403."""
    r = client.post(f"{env['base_nc']}{NCE}", token=tok, json_body=nota_credito(12345))
    a.status_in(r, *esperado)


@pytest.mark.nc
@pytest.mark.app
@pytest.mark.case_id("NC-022")
def test_nc_app_sin_jwt(client, env):
    """/v1/app/nota-credito sin JWT: doc procesa; real probablemente 401 (H-03)."""
    r = client.post(f"{env['base_nc']}/v1/app/nota-credito", json_body=nota_credito(12345))
    a.sin_stacktrace(r)
    a.status_in(r, 200, 400, 401, 403, 422)


@pytest.mark.nc
@pytest.mark.parametrize("metodo", ["GET", "PUT", "DELETE"])
def test_nc_metodos(client, env, token, metodo):
    """Metodo != POST sobre /v1/nota-credito -> 405."""
    r = client.request(metodo, f"{env['base_nc']}{NCE}", token=token, json_body={})
    a.sin_stacktrace(r)
    a.status_in(r, 405)
