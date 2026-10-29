"""Suite F33U - campos desconocidos / tipoDte no soportado."""
import pytest

from utils import assertions as a
from utils.payloads import factura33

FE = "/v1/factura"


def _post(client, env, token, p, raw=None):
    return client.post(f"{env['base_recepcion']}{FE}", token=token,
                       json_body=p if raw is None else "__NONE__", raw_body=raw)


@pytest.mark.emision
@pytest.mark.parametrize("cid,mut", [
    ("F33U-001", lambda p: {**p, "campoNoExiste": "test", "otroExtra": 123}),
    ("F33U-002", lambda p: {**p, "receptor": {**p["receptor"], "campoNoExiste": "x"}}),
    ("F33U-003", lambda p: {**p, "items": [{**p["items"][0], "campoNoExiste": "x"}]}),
])
def test_campos_extra(client, env, token, budget, cid, mut):
    """Campo desconocido: la API debe ignorarlo o rechazarlo; NO debe eco ni persistir."""
    budget.check()
    p = mut(factura33())
    r = _post(client, env, token, p)
    emitido = budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, 200, 400)
    if r.status == 200:
        assert "campoNoExiste" not in (r.text or ""), "la API hace eco del campo desconocido"
    if emitido:
        folio = r.json["datosDTE"]["folio"]
        chk = client.post(f"{env['base_consultas']}/v1/app/dte/33/{folio}", token=token, json_body={"rutEmisor": env["user"]})
        if chk.status == 200:
            assert "campoNoExiste" not in (chk.text or ""), "campo desconocido persistido"


@pytest.mark.emision
@pytest.mark.parametrize("cid,tipo,esperado", [
    ("F33U-004", 61, (400,)),
    ("F33U-005a", 39, (400,)),
    ("F33U-005b", 56, (400,)),
    ("F33U-005c", 999, (400,)),
])
def test_tipodte_no_soportado(client, env, token, budget, cid, tipo, esperado):
    """tipoDte fuera de {33,34} en /v1/factura -> 400. Registrar respuesta exacta."""
    budget.check()
    r = _post(client, env, token, factura33(tipoDte=tipo))
    budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)


@pytest.mark.emision
@pytest.mark.case_id("F33U-006")
def test_clave_json_duplicada(client, env, token, budget):
    """JSON con 'montoTotal' repetido -> last-wins (200) o 400. Documentar."""
    budget.check()
    raw = ('{"rutEmisor":"10471336-K","tipoDte":33,'
           '"receptor":{"rut":"26461274-8","razonSocial":"E","giro":458,'
           '"direccion":"D","comuna":13101,"email":"a@b.cl"},'
           '"items":[{"numeroLinea":1,"nombreItem":"I","cantidad":1,'
           '"precioUnitarioNeto":100000,"monto":100000}],'
           '"montoNeto":100000,"montoIVA":19000,"montoTotal":119000,"montoTotal":1}')
    r = _post(client, env, token, None, raw=raw)
    budget.maybe_record("F33U-006", r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, 200, 400)
