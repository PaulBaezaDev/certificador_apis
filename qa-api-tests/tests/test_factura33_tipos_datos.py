"""Suite F33T - tipos de dato incorrectos (esperado 400)."""
import pytest

from utils import assertions as a
from utils.payloads import factura33, mutate

FE = "/v1/factura"

CASOS = [
    ("F33T-001a", "tipoDte", "33", (400, 200)),
    ("F33T-001b", "tipoDte", 33.0, (400, 200)),
    ("F33T-001c", "tipoDte", True, (400,)),
    ("F33T-001d", "tipoDte", [33], (400,)),
    ("F33T-002a", "items", {}, (400,)),
    ("F33T-002b", "items", "x", (400,)),
    ("F33T-002c", "items", 123, (400,)),
    ("F33T-003a", "receptor", [], (400,)),
    ("F33T-003b", "receptor", "x", (400,)),
    ("F33T-003c", "receptor", 123, (400,)),
    ("F33T-004a", "montoTotal", "119000", (400, 200)),
    ("F33T-004b", "montoTotal", True, (400,)),
    ("F33T-004c", "montoTotal", [119000], (400,)),
    ("F33T-005a", "rutEmisor", ["10471336-K"], (400, 403)),
    ("F33T-005b", "rutEmisor", {"v": "10471336-K"}, (400, 403)),
    ("F33T-006a", "items.0.cantidad", "1", (400, 200)),
    ("F33T-006b", "items.0.cantidad", True, (400,)),
    ("F33T-007", "movimientoGlobal", "D", (400,)),
    ("F33T-008", "receptor.giro", "abc", (400,)),
]


@pytest.mark.emision
@pytest.mark.parametrize("cid,path,valor,esperado", CASOS, ids=[c[0] for c in CASOS])
def test_tipo_incorrecto(client, env, token, budget, cid, path, valor, esperado):
    """Campo con tipo de dato incorrecto -> 400 (documentar coerciones)."""
    budget.check()
    r = client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=mutate(factura33(), path, valor))
    budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)
