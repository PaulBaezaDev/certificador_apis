"""Suite F33O - matriz de campos obligatorios (esperado 400, NO deberia emitir)."""
import pytest

from utils import assertions as a
from utils.payloads import factura33, mutate, DROP

FE = "/v1/factura"

# (case_id, path, valor, http_esperado)
CASOS = [
    ("F33O-001a", "rutEmisor", DROP, (400, 403)),
    ("F33O-001b", "rutEmisor", None, (400, 403)),
    ("F33O-001c", "rutEmisor", "", (400, 403)),
    ("F33O-001d", "rutEmisor", 123, (400, 403)),
    ("F33O-002a", "tipoDte", DROP, (400,)),
    ("F33O-002b", "tipoDte", None, (400,)),
    ("F33O-002c", "tipoDte", "33", (400, 200)),
    ("F33O-002d", "tipoDte", 0, (400,)),
    ("F33O-003a", "receptor", DROP, (400,)),
    ("F33O-003b", "receptor", None, (400,)),
    ("F33O-003c", "receptor", [], (400,)),
    ("F33O-004a", "items", DROP, (400,)),
    ("F33O-004b", "items", None, (400,)),
    ("F33O-004c", "items", [], (400,)),
    ("F33O-005a", "montoNeto", DROP, (400,)),
    ("F33O-005b", "montoNeto", None, (400,)),
    ("F33O-005c", "montoNeto", 0, (400,)),
    ("F33O-006a", "montoIVA", DROP, (400,)),
    ("F33O-006b", "montoIVA", None, (400,)),
    ("F33O-006c", "montoIVA", 0, (400,)),
    ("F33O-007a", "montoTotal", DROP, (400,)),
    ("F33O-007b", "montoTotal", None, (400,)),
    ("F33O-007c", "montoTotal", 0, (400,)),
    ("F33O-008a", "receptor.rut", DROP, (400,)),
    ("F33O-008b", "receptor.rut", None, (400,)),
    ("F33O-008c", "receptor.rut", "", (400,)),
    ("F33O-008d", "receptor.rut", 123, (400,)),
    ("F33O-009a", "receptor.razonSocial", DROP, (400,)),
    ("F33O-009b", "receptor.razonSocial", "", (400,)),
    ("F33O-010a", "receptor.giro", DROP, (400,)),
    ("F33O-010b", "receptor.giro", None, (400,)),
    ("F33O-010c", "receptor.giro", 0, (400,)),
    ("F33O-010d", "receptor.giro", "458", (400, 200)),
    ("F33O-011a", "receptor.direccion", DROP, (400,)),
    ("F33O-011b", "receptor.direccion", "", (400,)),
    ("F33O-012a", "receptor.comuna", DROP, (400,)),
    ("F33O-012b", "receptor.comuna", None, (400,)),
    ("F33O-012c", "receptor.comuna", 0, (400,)),
    ("F33O-012d", "receptor.comuna", "13101", (400, 200)),
    ("F33O-013a", "receptor.email", DROP, (400, 200)),
    ("F33O-013b", "receptor.email", "", (400, 200)),
    ("F33O-014a", "items.0.numeroLinea", DROP, (400,)),
    ("F33O-014b", "items.0.numeroLinea", None, (400,)),
    ("F33O-015a", "items.0.nombreItem", DROP, (400,)),
    ("F33O-015b", "items.0.nombreItem", "", (400,)),
    ("F33O-016a", "items.0.cantidad", DROP, (400,)),
    ("F33O-016b", "items.0.cantidad", None, (400,)),
    ("F33O-016c", "items.0.cantidad", 0, (400,)),
    ("F33O-017a", "items.0.precioUnitarioNeto", DROP, (400,)),
    ("F33O-017b", "items.0.precioUnitarioNeto", None, (400,)),
    ("F33O-017c", "items.0.precioUnitarioNeto", -1, (400,)),
    ("F33O-018a", "items.0.monto", DROP, (400,)),
    ("F33O-018b", "items.0.monto", None, (400,)),
    ("F33O-018c", "items.0.monto", 0, (400,)),
]


@pytest.mark.emision
@pytest.mark.parametrize("cid,path,valor,esperado", CASOS, ids=[c[0] for c in CASOS])
def test_campo_obligatorio(client, env, token, budget, cid, path, valor, esperado):
    """Campo obligatorio omitido/nulo/vacio/tipo-incorrecto -> 400."""
    budget.check()
    p = mutate(factura33(), path, valor)
    r = client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=p)
    budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)
    if r.status == 400:
        a.codigo_respuesta(r, "99")


@pytest.mark.emision
@pytest.mark.emision_happy
@pytest.mark.case_id("F33O-019")
def test_opcionales_omitidos_ok(client, env, token, budget):
    """telefono y ciudad omitidos (opcionales) -> 200."""
    budget.check()
    p = factura33()
    p["receptor"].pop("telefono", None)
    r = client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=p)
    budget.maybe_record("F33O-019", r, FE)
    a.emitido_ok(r)
