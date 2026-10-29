"""Suite F33M - reglas tributarias y consistencia de montos (CRITICAL).

Objetivo O-01: determinar si la API recalcula montos o confia en los enviados.
Los casos que pueden devolver 200 se ejecutan con presupuesto (<=6 DTE aqui).
"""
import pytest

from utils import assertions as a
from utils.payloads import factura33, mutate

FE = "/v1/factura"


def _post(client, env, token, p):
    return client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=p)


# --- casos que DEBEN ser rechazados (400) ---
RECHAZO = [
    ("F33M-001", "montoNeto", -100000),
    ("F33M-002", "montoIVA", -19000),
    ("F33M-003", "montoTotal", -119000),
    ("F33M-004", "items.0.precioUnitarioNeto", -100000),
    ("F33M-005", "items.0.cantidad", -1),
    ("F33M-006", "items.0.cantidad", 0),
    ("F33M-007", "items.0.monto", -100000),
    ("F33M-013", "montoNeto", 100000.5),
    ("F33M-021", "montoIVA", 0),
]


@pytest.mark.emision
@pytest.mark.parametrize("cid,path,valor", RECHAZO, ids=[c[0] for c in RECHAZO])
def test_montos_invalidos_rechazo(client, env, token, budget, cid, path, valor):
    """Monto/cantidad invalido -> 400 codigoRespuesta 99."""
    budget.check()
    r = _post(client, env, token, mutate(factura33(), path, valor))
    budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, 400)


# --- casos O-01: inconsistencias que revelan si valida o confia ---
@pytest.mark.emision
@pytest.mark.case_id("F33M-008")
def test_neto_distinto_suma_items(client, env, token, budget):
    """montoNeto inflado != sum(items.monto): documentar 400 vs 200 (y que persiste)."""
    budget.check()
    p = factura33(montoNeto=999999, montoIVA=190000, montoTotal=1189999)
    r = _post(client, env, token, p)
    emitido = budget.maybe_record("F33M-008", r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, 400)  # contrato: deberia validar coherencia
    if emitido:
        pytest.fail("POSIBLE DEFECTO: emitio DTE con montoNeto != suma de items")


@pytest.mark.emision
@pytest.mark.case_id("F33M-009")
def test_iva_no_es_19_por_ciento(client, env, token, budget):
    """montoIVA = 1 (no 19% del neto): 400 esperado."""
    budget.check()
    p = factura33(montoNeto=100000, montoIVA=1, montoTotal=100001)
    r = _post(client, env, token, p)
    emitido = budget.maybe_record("F33M-009", r, FE)
    a.status_in(r, 400)
    if emitido:
        pytest.fail("POSIBLE DEFECTO: emitio DTE con IVA != 19%")


@pytest.mark.emision
@pytest.mark.case_id("F33M-010")
def test_total_distinto_neto_mas_iva(client, env, token, budget):
    """montoTotal != montoNeto + montoIVA -> 400."""
    budget.check()
    p = factura33(montoNeto=100000, montoIVA=19000, montoTotal=1)
    r = _post(client, env, token, p)
    emitido = budget.maybe_record("F33M-010", r, FE)
    a.status_in(r, 400)
    if emitido:
        pytest.fail("POSIBLE DEFECTO: emitio DTE con total != neto + iva")


@pytest.mark.emision
@pytest.mark.emision_happy
@pytest.mark.case_id("F33M-012")
def test_baseline_montos_coherentes(client, env, token, budget):
    """Montos correctos -> 200. Se compara respuesta vs enviado (O-01 baseline)."""
    budget.check()
    p = factura33()  # 100000 / 19000 / 119000
    r = _post(client, env, token, p)
    budget.maybe_record("F33M-012", r, FE)
    datos = a.emitido_ok(r)
    # registrar para el reporte si la API devuelve los mismos montos o recalcula
    assert datos.get("montoTotal") in (119000, None), \
        f"montoTotal devuelto: {datos.get('montoTotal')} (enviado 119000)"


@pytest.mark.emision
@pytest.mark.parametrize("cid,valor,esperado", [
    ("F33M-014", 9_999_999_999_999, (400, 500)),
    ("F33M-015", "1e6", (400,)),
])
def test_montos_extremos(client, env, token, budget, cid, valor, esperado):
    """Valores extremos en montoTotal -> 400 (documentar 500)."""
    budget.check()
    p = factura33()
    p["montoTotal"] = valor
    r = _post(client, env, token, p)
    budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)


@pytest.mark.emision
@pytest.mark.parametrize("cid,mov,esperado", [
    ("F33M-016", {"tipo": "D", "tipoValor": "$", "monto": 200000}, (400,)),   # dcto > linea
    ("F33M-017", {"tipo": "D", "tipoValor": "%", "porcentaje": 150, "monto": 150000}, (400,)),
    ("F33M-019", {"tipo": "X", "tipoValor": "$", "monto": 10}, (400,)),
    ("F33M-020", {"tipo": "D", "tipoValor": "%", "monto": 10}, (400,)),        # % sin porcentaje
])
def test_movimiento_item_invalido(client, env, token, budget, cid, mov, esperado):
    """movimientoItem invalido -> 400."""
    budget.check()
    p = factura33()
    p["items"][0]["movimientoItem"] = mov
    r = _post(client, env, token, p)
    budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)


@pytest.mark.emision
@pytest.mark.case_id("F33M-018")
def test_movimiento_global_mayor_que_total(client, env, token, budget):
    """movimientoGlobal descuento > total del documento -> 400."""
    budget.check()
    p = factura33()
    p["movimientoGlobal"] = {"tipoMovimiento": "D", "tipoValor": "$", "monto": 10_000_000}
    r = _post(client, env, token, p)
    budget.maybe_record("F33M-018", r, FE)
    a.status_in(r, 400)
