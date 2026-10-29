"""Suite F34 - Factura Exenta tipo 34 (CRITICAL). Foco: comportamiento del IVA."""
import pytest

from utils import assertions as a
from utils.payloads import factura34, mutate

FE = "/v1/factura"


def _post(client, env, token, p):
    return client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=p)


@pytest.mark.emision
@pytest.mark.emision_happy
@pytest.mark.case_id("F34-001")
def test_exenta_minima(client, env, token, budget):
    """Exenta minima (solo montoTotal) -> 200, montoExento == montoTotal, sin IVA."""
    budget.check()
    r = _post(client, env, token, factura34())
    budget.maybe_record("F34-001", r, FE)
    datos = a.emitido_ok(r)
    assert datos["tipoDte"] == 34
    assert datos.get("montoExento") == 45000, f"montoExento={datos.get('montoExento')}"
    assert "montoIVA" not in datos and "montoIva" not in datos, "exenta no debe traer IVA"


@pytest.mark.emision
@pytest.mark.emision_happy
@pytest.mark.case_id("F34-002")
def test_exenta_varias_lineas(client, env, token, budget):
    """Exenta con 3 lineas -> 200."""
    budget.check()
    items = [{"numeroLinea": i, "nombreItem": f"Servicio {i}", "cantidad": 1,
              "precioUnitarioNeto": 10000, "monto": 10000} for i in range(1, 4)]
    r = _post(client, env, token, factura34(items=items, montoTotal=30000))
    budget.maybe_record("F34-002", r, FE)
    a.emitido_ok(r)


@pytest.mark.emision
@pytest.mark.emision_happy
@pytest.mark.case_id("F34-003")
def test_exenta_con_iva_positivo(client, env, token, budget):
    """CLAVE: exenta con montoIVA > 0. Manual: se ignora. Documentar exacto:
    rechaza / ignora / recalcula / emite igual."""
    budget.check()
    p = factura34(montoNeto=45000, montoIVA=8550)
    r = _post(client, env, token, p)
    emitido = budget.maybe_record("F34-003", r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, 200, 400)
    if emitido:
        datos = r.json["datosDTE"]
        assert datos.get("montoExento") == 45000
        assert not datos.get("montoIVA") and not datos.get("montoIva"), \
            f"POSIBLE DEFECTO: exenta emitida CON IVA {datos}"


@pytest.mark.emision
@pytest.mark.emision_happy
@pytest.mark.case_id("F34-004")
def test_exenta_con_neto(client, env, token, budget):
    """Exenta con montoNeto > 0: manual dice que se ignora -> 200."""
    budget.check()
    r = _post(client, env, token, factura34(montoNeto=50000))
    budget.maybe_record("F34-004", r, FE)
    a.status_in(r, 200, 400)


@pytest.mark.emision
@pytest.mark.emision_happy
@pytest.mark.case_id("F34-005")
def test_exenta_montos_incoherentes(client, env, token, budget):
    """montoNeto + montoIVA + montoTotal incoherentes: ignora neto/iva -> 200, exento=total."""
    budget.check()
    p = factura34(montoNeto=999, montoIVA=111, montoTotal=45000)
    r = _post(client, env, token, p)
    emitido = budget.maybe_record("F34-005", r, FE)
    a.status_in(r, 200, 400)
    if emitido:
        assert r.json["datosDTE"].get("montoExento") == 45000


@pytest.mark.emision
@pytest.mark.parametrize("cid,path,valor,esperado", [
    ("F34-006", "montoIVA", -1000, (200, 400)),
    ("F34-007", "montoIVA", None, (200, 400)),
    ("F34-008", "montoTotal", 0, (400,)),
    ("F34-009", "montoTotal", -45000, (400,)),
    ("F34-010", "montoTotal", None, (400,)),
    ("F34-011", "montoTotal", 9_999_999_999_999, (400, 200, 500)),
    ("F34-015a", "items.0.cantidad", 0, (400,)),
    ("F34-015b", "items.0.cantidad", -1, (400,)),
    ("F34-019", "montoNeto", "50000", (200, 400)),
])
def test_f34_mutaciones(client, env, token, budget, cid, path, valor, esperado):
    """Mutaciones de montos/cantidad en exenta."""
    budget.check()
    r = _post(client, env, token, mutate(factura34(), path, valor))
    budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)


@pytest.mark.emision
@pytest.mark.case_id("F34-013")
def test_items_duplicados(client, env, token, budget):
    """Dos items con numeroLinea repetido -> 400 esperado (documentar si 200)."""
    budget.check()
    it = {"numeroLinea": 1, "nombreItem": "X", "cantidad": 1, "precioUnitarioNeto": 1000, "monto": 1000}
    r = _post(client, env, token, factura34(items=[it, dict(it)], montoTotal=2000))
    emitido = budget.maybe_record("F34-013", r, FE)
    a.status_in(r, 200, 400)
    if emitido:
        pytest.fail("POSIBLE DEFECTO: emitio con numeroLinea duplicado")


@pytest.mark.emision
@pytest.mark.case_id("F34-014")
def test_numlinea_no_secuencial(client, env, token, budget):
    """numeroLinea no secuencial (1,3,7) -> 400 o 200 (documentar)."""
    budget.check()
    items = [{"numeroLinea": n, "nombreItem": f"L{n}", "cantidad": 1,
              "precioUnitarioNeto": 1000, "monto": 1000} for n in (1, 3, 7)]
    r = _post(client, env, token, factura34(items=items, montoTotal=3000))
    budget.maybe_record("F34-014", r, FE)
    a.status_in(r, 200, 400)


@pytest.mark.emision
@pytest.mark.parametrize("cid,mut", [
    ("F34-016a", lambda p: {k: v for k, v in p.items() if k != "rutEmisor"}),
    ("F34-016b", lambda p: {k: v for k, v in p.items() if k != "items"}),
    ("F34-016c", lambda p: {k: v for k, v in p.items() if k != "montoTotal"}),
    ("F34-016d", lambda p: {**p, "receptor": {k: v for k, v in p["receptor"].items() if k != "rut"}}),
])
def test_f34_obligatorios(client, env, token, budget, cid, mut):
    """Campos obligatorios de exenta omitidos -> 400."""
    budget.check()
    r = _post(client, env, token, mut(factura34()))
    budget.maybe_record(cid, r, FE)
    a.status_in(r, 400, 403)


@pytest.mark.emision
@pytest.mark.case_id("F34-018")
def test_verificacion_post_emision(client, env, token, emitted_f34):
    """POST /v1/app/dte/34/{folio}: montos condicionales -> montoExento + montoTotal, sin neto/iva."""
    folio = emitted_f34["folio"]
    r = client.post(f"{env['base_consultas']}/v1/app/dte/34/{folio}", token=token, json_body={"rutEmisor": env["user"]})
    a.status_in(r, 200)
    df = r.json["datosFactura"]
    assert df["tipoDte"] == 34
    assert "montoExento" in df and "montoTotal" in df
    assert "montoNeto" not in df and "montoIva" not in df
