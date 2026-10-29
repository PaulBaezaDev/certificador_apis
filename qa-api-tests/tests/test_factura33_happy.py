"""Suite F33H - Factura 33 camino feliz (CRITICAL). GENERA DTE REAL."""
import pytest

from utils import assertions as a
from utils.payloads import factura33, factura33_completa


FE = "/v1/factura"


def _post(client, env, token, payload):
    return client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=payload)


@pytest.mark.emision
@pytest.mark.emision_happy
@pytest.mark.case_id("F33H-001")
def test_minimo(client, env, token, budget):
    """Request minimo valido -> 200 codigoRespuesta 01, folio, timbrePDF417."""
    budget.check()
    r = _post(client, env, token, factura33())
    budget.maybe_record("F33H-001", r, FE)
    datos = a.emitido_ok(r)
    assert datos["tipoDte"] == 33
    assert "timbrePDF417" in datos


@pytest.mark.emision
@pytest.mark.emision_happy
@pytest.mark.case_id("F33H-002")
def test_completo(client, env, token, budget):
    """Request completo (2 items, movimientoItem %, movimientoGlobal) -> 200."""
    budget.check()
    p = factura33_completa()
    p["movimientoGlobal"] = {"tipoMovimiento": "D", "tipoValor": "$", "monto": 25000,
                             "descripcion": "Descuento cliente"}
    r = _post(client, env, token, p)
    budget.maybe_record("F33H-002", r, FE)
    a.emitido_ok(r)


@pytest.mark.emision
@pytest.mark.emision_happy
@pytest.mark.case_id("F33H-004")
def test_diez_lineas(client, env, token, budget):
    """10 lineas (limite maximo) -> 200."""
    budget.check()
    items = [{"numeroLinea": i, "nombreItem": f"Item {i}", "cantidad": 1,
              "precioUnitarioNeto": 1000, "monto": 1000} for i in range(1, 11)]
    p = factura33(items=items, montoNeto=10000, montoIVA=1900, montoTotal=11900)
    r = _post(client, env, token, p)
    budget.maybe_record("F33H-004", r, FE)
    a.emitido_ok(r)


@pytest.mark.case_id("F33H-005")
@pytest.mark.emision
def test_once_lineas(client, env, token, budget):
    """11 lineas (sobre el limite 1..10) -> 400."""
    budget.check()
    items = [{"numeroLinea": i, "nombreItem": f"Item {i}", "cantidad": 1,
              "precioUnitarioNeto": 1000, "monto": 1000} for i in range(1, 12)]
    p = factura33(items=items, montoNeto=11000, montoIVA=2090, montoTotal=13090)
    r = _post(client, env, token, p)
    budget.maybe_record("F33H-005", r, FE)
    a.status_in(r, 400)


@pytest.mark.emision
@pytest.mark.emision_happy
@pytest.mark.case_id("F33H-006")
def test_cantidad_decimales(client, env, token, budget):
    """cantidad con 4 decimales -> 200 (o 400 si exige entero)."""
    budget.check()
    p = factura33()
    p["items"][0].update({"cantidad": 2.5, "precioUnitarioNeto": 40000, "monto": 100000})
    r = _post(client, env, token, p)
    budget.maybe_record("F33H-006", r, FE)
    a.status_in(r, 200, 400)


@pytest.mark.emision
@pytest.mark.case_id("F33H-007")
def test_verificacion_post_emision(client, env, token, emitted_f33):
    """POST /v1/app/dte/33/{folio} del DTE emitido -> 200, datos coinciden."""
    folio = emitted_f33["folio"]
    r = client.post(f"{env['base_consultas']}/v1/app/dte/33/{folio}", token=token, json_body={"rutEmisor": env["user"]})
    a.status_in(r, 200)
    df = r.json["datosFactura"]
    assert df["folio"] == folio and df["tipoDte"] == 33
    assert df.get("estado"), "sin estado en la consulta"
