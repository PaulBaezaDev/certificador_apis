"""Suite F33S - campos string: limites, unicode, inyecciones (aplicado a razonSocial / nombreItem)."""
import pytest

from utils import assertions as a
from utils.payloads import factura33, mutate

FE = "/v1/factura"


def _post(client, env, token, p):
    return client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=p)


@pytest.mark.emision
@pytest.mark.emision_happy
@pytest.mark.case_id("F33S-001")
def test_string_valido_baseline(client, env, token, budget):
    """String normal -> 200 (baseline)."""
    budget.check()
    r = _post(client, env, token, factura33())
    budget.maybe_record("F33S-001", r, FE)
    a.emitido_ok(r)


@pytest.mark.emision
@pytest.mark.parametrize("cid,valor,esperado", [
    ("F33S-002a", "", (400,)),
    ("F33S-002b", "   ", (400,)),
    ("F33S-002c", "  Empresa  ", (200, 400)),
    ("F33S-003", "X" * 10000, (200, 400)),
    ("F33S-005a", "linea1\nlinea2", (200, 400)),
    ("F33S-005b", "tab\tsep", (200, 400)),
    ("F33S-009", "esc\\x00\\u0000", (200, 400)),
])
def test_razon_social_mutaciones(client, env, token, budget, cid, valor, esperado):
    """razonSocial: vacio/espacios/largo/saltos/escape -> 400 o 200 (documentar)."""
    budget.check()
    r = _post(client, env, token, mutate(factura33(), "receptor.razonSocial", valor))
    budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, *esperado)


@pytest.mark.emision
@pytest.mark.parametrize("cid,valor", [
    ("F33S-004a", "Empresa Ñandú 中文 𝕏"),
    ("F33S-004b", "Emoji Corp 🚀🔥✅"),
])
def test_unicode_emojis(client, env, token, budget, cid, valor):
    """Unicode/emojis en nombreItem -> 200 y se persiste correctamente (verificar)."""
    budget.check()
    p = factura33()
    p["items"][0]["nombreItem"] = valor
    r = _post(client, env, token, p)
    emitido = budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, 200, 400)
    if emitido:
        folio = r.json["datosDTE"]["folio"]
        chk = client.post(f"{env['base_consultas']}/v1/app/dte/33/{folio}", token=token, json_body={"rutEmisor": env["user"]})
        if chk.status == 200:
            persistido = chk.json["datosFactura"]["items"][0]["nombreItem"]
            assert persistido == valor, f"persistio '{persistido}' != enviado '{valor}'"


@pytest.mark.emision
@pytest.mark.seguridad
@pytest.mark.parametrize("cid,campo,valor", [
    ("F33S-006", "receptor.razonSocial", "<b>Empresa</b> <i>SpA</i>"),
    ("F33S-007", "items.0.nombreItem", "<script>alert(1)</script>"),
    ("F33S-008", "receptor.razonSocial", "x'; DROP TABLE dte;-- "),
    ("F33S-008b", "items.0.nombreItem", "1' OR '1'='1"),
])
def test_inyecciones_en_strings(client, env, token, budget, cid, campo, valor):
    """HTML/XSS/SQLi en strings -> se trata como texto plano, sin error SQL ni ejecucion."""
    budget.check()
    r = _post(client, env, token, mutate(factura33(), campo, valor))
    emitido = budget.maybe_record(cid, r, FE)
    a.sin_stacktrace(r)
    a.status_in(r, 200, 400)
    if emitido:
        folio = r.json["datosDTE"]["folio"]
        chk = client.post(f"{env['base_consultas']}/v1/app/dte/33/{folio}", token=token, json_body={"rutEmisor": env["user"]})
        a.sin_stacktrace(chk)


@pytest.mark.emision
@pytest.mark.parametrize("cid,valor,esperado", [
    ("F33S-010a", "abc", (400, 200)),
    ("F33S-010b", "sin-arroba.cl", (400, 200)),
    ("F33S-010c", "a@b@c.cl", (400, 200)),
])
def test_email_formato(client, env, token, budget, cid, valor, esperado):
    """receptor.email con formato invalido -> 400 (documentar si no valida)."""
    budget.check()
    r = _post(client, env, token, mutate(factura33(), "receptor.email", valor))
    budget.maybe_record(cid, r, FE)
    a.status_in(r, *esperado)
