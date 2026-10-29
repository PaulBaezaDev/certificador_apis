"""Genera la Postman Collection 'DTE API Testing' + environments QA/DEV.

Fuente unica: este script (alineado con docs/02_matriz_pruebas.md). Salida:
  ../DTE API Testing.postman_collection.json
  ../DTE API Testing - QA.postman_environment.json
  ../DTE API Testing - DEV.postman_environment.json
  ../DTE API Testing - DUMMYS.postman_environment.json
"""
import json
import pathlib
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT.parent  # raiz del proyecto

RECEPTOR = {
    "rut": "{{rutReceptor}}", "razonSocial": "Empresa Receptora SpA", "giro": 458,
    "direccion": "Av. Providencia 1234", "comuna": 13101,
    "email": "factura@empresa.cl", "telefono": "92323420",
}
F33 = {
    "rutEmisor": "{{rutEmisor}}", "tipoDte": 33, "receptor": RECEPTOR,
    "items": [{"numeroLinea": 1, "nombreItem": "Servicio QA", "cantidad": 1,
               "precioUnitarioNeto": 100000, "monto": 100000}],
    "montoNeto": 100000, "montoIVA": 19000, "montoTotal": 119000,
}
F34 = {
    "rutEmisor": "{{rutEmisor}}", "tipoDte": 34, "receptor": RECEPTOR,
    "items": [{"numeroLinea": 1, "nombreItem": "Consulta medica", "cantidad": 1,
               "precioUnitarioNeto": 45000, "monto": 45000}],
    "montoTotal": 45000,
}
NC = {
    "codigoReferencia": 1, "razonReferencia": "Anula por error en datos",
    "rutEmisor": "{{rutEmisor}}",
    "receptor": {"rut": "{{rutReceptor}}", "razonSocial": "Empresa Receptora SpA",
                 "giro": "Edicion de programas informaticos", "direccion": "Av. Providencia 1234",
                 "comuna": "Santiago", "email": "factura@empresa.cl", "telefono": "92323420"},
    "datosFactura": {"tipoDte": 33, "folio": "{{folioFactura}}",
                     "items": [{"numeroLinea": 1, "nombreItem": "Servicio QA", "cantidad": 1,
                                "precioUnitarioNeto": 100000, "monto": 100000}],
                     "montoNeto": 100000, "montoIVA": 19000, "montoTotal": 119000},
}


def _mut(base, path, value):
    import copy
    o = copy.deepcopy(base)
    keys = path.split(".")
    n = o
    for k in keys[:-1]:
        k = int(k) if k.isdigit() else k
        n = n[k]
    last = keys[-1]
    if value == "__DROP__":
        n.pop(int(last) if last.isdigit() else last, None)
    else:
        n[int(last) if last.isdigit() else last] = value
    return o


def _test(lines):
    return {"listen": "test", "script": {"type": "text/javascript", "exec": lines}}


def status_test(*codes):
    arr = ", ".join(str(c) for c in codes)
    return _test([
        f"pm.test('HTTP en [{arr}]', () => pm.expect([{arr}]).to.include(pm.response.code));",
        "pm.test('responde JSON', () => pm.response.to.be.json || pm.response.code >= 500);",
    ])


def emision_test():
    return _test([
        "pm.test('HTTP 200', () => pm.response.to.have.status(200));",
        "const b = pm.response.json();",
        "pm.test('codigoRespuesta 01', () => pm.expect(b.codigoRespuesta).to.eql('01'));",
        "pm.test('trae folio', () => pm.expect(b.datosDTE.folio).to.be.a('number'));",
        "if (b.datosDTE && b.datosDTE.folio) pm.collectionVariables.set('folioFactura', b.datosDTE.folio);",
    ])


def req(name, method, url, *, auth=True, body=None, tests=None, raw_body=None, headers=None):
    h = list(headers or [])
    r = {
        "name": name,
        "request": {
            "method": method,
            "header": h,
            "url": {"raw": url, "host": ["{{baseUrl}}"], "path": url.replace("{{baseUrl}}/", "").split("/")},
        },
    }
    if auth:
        r["request"]["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "{{jwt}}", "type": "string"}]}
    else:
        r["request"]["auth"] = {"type": "noauth"}
    if body is not None:
        h.append({"key": "Content-Type", "value": "application/json"})
        r["request"]["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2, ensure_ascii=False),
                                "options": {"raw": {"language": "json"}}}
    elif raw_body is not None:
        r["request"]["body"] = {"mode": "raw", "raw": raw_body}
    if tests:
        r["event"] = [tests]
    return r


def folder(name, items):
    return {"name": name, "item": items}


def build_qa():
    login = req("000 - Login QA (setea jwt)", "POST",
                "https://apiqa.mcdesaqa.cl/public/auth/web/v1/login", auth=False,
                body={"user": "{{loginUser}}", "pass": "{{loginPass}}"},
                tests=_test([
                    "const b = pm.response.json();",
                    "if (b.data && b.data.token) pm.collectionVariables.set('jwt', b.data.token);",
                    "pm.test('token generado', () => pm.expect(b.code).to.eql(1));",
                ]))
    login["request"]["url"] = {"raw": "https://apiqa.mcdesaqa.cl/public/auth/web/v1/login"}

    f33 = folder("01 - Factura Tipo 33", [
        folder("001 - Happy Path", [
            req("F33H-001 minimo", "POST", "{{baseUrl}}/v1/factura", body=F33, tests=emision_test()),
            req("F33H-002 completo", "POST", "{{baseUrl}}/v1/factura",
                body={**F33, "montoNeto": 610000, "montoIVA": 115900, "montoTotal": 725900,
                      "items": [
                          {"numeroLinea": 1, "nombreItem": "Consultoria", "cantidad": 10,
                           "precioUnitarioNeto": 50000, "monto": 450000,
                           "movimientoItem": {"tipo": "D", "tipoValor": "%", "porcentaje": 10, "monto": 50000}},
                          {"numeroLinea": 2, "nombreItem": "Licencia", "cantidad": 2,
                           "precioUnitarioNeto": 80000, "monto": 160000}],
                      "movimientoGlobal": {"tipoMovimiento": "D", "tipoValor": "$", "monto": 25000}},
                tests=emision_test()),
        ]),
        folder("002 - Campos obligatorios", [
            req(f"F33O {p}={v}", "POST", "{{baseUrl}}/v1/factura", body=_mut(F33, p, v), tests=status_test(400))
            for p, v in [("rutEmisor", "__DROP__"), ("tipoDte", "__DROP__"), ("receptor", "__DROP__"),
                         ("items", []), ("montoNeto", "__DROP__"), ("montoIVA", "__DROP__"),
                         ("montoTotal", "__DROP__"), ("receptor.rut", "__DROP__"),
                         ("receptor.giro", "__DROP__"), ("receptor.comuna", "__DROP__"),
                         ("items.0.monto", "__DROP__"), ("items.0.cantidad", 0)]
        ]),
        folder("003 - Montos / reglas tributarias", [
            req("F33M-001 neto negativo", "POST", "{{baseUrl}}/v1/factura",
                body=_mut(F33, "montoNeto", -100000), tests=status_test(400)),
            req("F33M-008 neto != suma items", "POST", "{{baseUrl}}/v1/factura",
                body={**F33, "montoNeto": 999999, "montoIVA": 190000, "montoTotal": 1189999},
                tests=status_test(400)),
            req("F33M-009 IVA != 19%", "POST", "{{baseUrl}}/v1/factura",
                body={**F33, "montoIVA": 1, "montoTotal": 100001}, tests=status_test(400)),
            req("F33M-010 total != neto+iva", "POST", "{{baseUrl}}/v1/factura",
                body={**F33, "montoTotal": 1}, tests=status_test(400)),
            req("F33M-021 IVA=0 en afecta", "POST", "{{baseUrl}}/v1/factura",
                body=_mut(F33, "montoIVA", 0), tests=status_test(400)),
        ]),
        folder("004 - RUT", [
            req("RUT-006 DV incorrecto", "POST", "{{baseUrl}}/v1/factura",
                body=_mut(F33, "rutEmisor", "10471336-0"), tests=status_test(400)),
            req("RUT-021 rutEmisor != sub JWT", "POST", "{{baseUrl}}/v1/factura",
                body=_mut(F33, "rutEmisor", "77151256-9"), tests=status_test(403)),
            req("RUT-010 rutEmisor vacio", "POST", "{{baseUrl}}/v1/factura",
                body=_mut(F33, "rutEmisor", ""), tests=status_test(400, 403)),
            req("RUT-020 receptor.rut DV malo", "POST", "{{baseUrl}}/v1/factura",
                body=_mut(F33, "receptor.rut", "26461274-0"), tests=status_test(400)),
        ]),
        folder("005 - Tipos de dato / desconocidos", [
            req("F33T-001 tipoDte string", "POST", "{{baseUrl}}/v1/factura",
                body=_mut(F33, "tipoDte", "33"), tests=status_test(400, 200)),
            req("F33U-001 campo desconocido", "POST", "{{baseUrl}}/v1/factura",
                body={**F33, "campoNoExiste": "test"}, tests=status_test(200, 400)),
            req("F33U-004 tipoDte 61 en /v1/factura", "POST", "{{baseUrl}}/v1/factura",
                body=_mut(F33, "tipoDte", 61), tests=status_test(400)),
        ]),
        folder("006 - Seguridad / HTTP", [
            req("F33X-006 GET sobre /v1/factura", "GET", "{{baseUrl}}/v1/factura", tests=status_test(405)),
            req("F33X-001 Content-Type text/plain", "POST", "{{baseUrl}}/v1/factura",
                raw_body=json.dumps(F33), headers=[{"key": "Content-Type", "value": "text/plain"}],
                tests=status_test(415, 400)),
            req("F33X-003 body vacio", "POST", "{{baseUrl}}/v1/factura", raw_body="",
                headers=[{"key": "Content-Type", "value": "application/json"}], tests=status_test(400)),
            req("F33S-008 SQLi en razonSocial", "POST", "{{baseUrl}}/v1/factura",
                body=_mut(F33, "receptor.razonSocial", "x'; DROP TABLE dte;--"), tests=status_test(200, 400)),
        ]),
        folder("007 - Duplicidad", [
            req(f"DUP-001 reenvio {i}", "POST", "{{baseUrl}}/v1/factura", body=F33, tests=status_test(200, 409))
            for i in (1, 2, 3)
        ]),
        folder("008 - Autenticacion", [
            req("AUTH-002 sin token", "POST", "{{baseUrl}}/v1/factura", auth=False, body=F33, tests=status_test(401)),
            req("AUTH-009 firma alterada", "POST", "{{baseUrl}}/v1/factura", body=F33,
                headers=[{"key": "Authorization", "value": "Bearer {{jwt}}X"}], tests=status_test(401, 403)),
        ]),
    ])

    f34 = folder("02 - Factura Tipo 34", [
        folder("001 - Happy Path", [req("F34-001 exenta minima", "POST", "{{baseUrl}}/v1/factura",
                                        body=F34, tests=emision_test())]),
        folder("002 - IVA en exenta", [
            req("F34-003 exenta con IVA>0", "POST", "{{baseUrl}}/v1/factura",
                body={**F34, "montoNeto": 45000, "montoIVA": 8550}, tests=status_test(200, 400)),
            req("F34-006 exenta con IVA negativo", "POST", "{{baseUrl}}/v1/factura",
                body={**F34, "montoIVA": -1000}, tests=status_test(200, 400)),
        ]),
        folder("003 - Montos", [
            req("F34-008 total 0", "POST", "{{baseUrl}}/v1/factura",
                body=_mut(F34, "montoTotal", 0), tests=status_test(400)),
            req("F34-009 total negativo", "POST", "{{baseUrl}}/v1/factura",
                body=_mut(F34, "montoTotal", -45000), tests=status_test(400)),
        ]),
        folder("004 - Datos invalidos", [
            req("F34-013 items duplicados", "POST", "{{baseUrl}}/v1/factura",
                body={**F34, "items": [F34["items"][0], dict(F34["items"][0])], "montoTotal": 90000},
                tests=status_test(200, 400)),
        ]),
    ])

    nc = folder("03 - Nota de Credito Tipo 61", [
        req("NC-001 tipo 61 a /v1/factura", "POST", "{{baseUrl}}/v1/factura",
            body=_mut(F33, "tipoDte", 61), tests=status_test(400)),
        req("NC-002 happy (requiere folio ACEPTADO)", "POST", "{{baseUrlNc}}/v1/nota-credito",
            body=NC, tests=status_test(200, 422, 400)),
        req("NC-005 folio referencia inexistente", "POST", "{{baseUrlNc}}/v1/nota-credito",
            body=_mut(NC, "datosFactura.folio", 999999999), tests=status_test(422, 404, 400)),
        req("NC-010 monto NC > original", "POST", "{{baseUrlNc}}/v1/nota-credito",
            body=_mut(NC, "datosFactura.montoTotal", 999999999), tests=status_test(400, 422)),
        req("NC-014 codigoReferencia invalido", "POST", "{{baseUrlNc}}/v1/nota-credito",
            body=_mut(NC, "codigoReferencia", 99), tests=status_test(400, 422)),
        req("NC-018 NC duplicada", "POST", "{{baseUrlNc}}/v1/nota-credito", body=NC,
            tests=status_test(409, 422, 200)),
        req("NC-020 sub != rutEmisor", "POST", "{{baseUrlNc}}/v1/nota-credito",
            body=_mut(NC, "rutEmisor", "77151256-9"), tests=status_test(403)),
        req("NC-021 sin token", "POST", "{{baseUrlNc}}/v1/nota-credito", auth=False, body=NC,
            tests=status_test(401)),
    ])

    regiones = folder("04 - Regiones", [
        req("REG-001 happy", "GET", "{{baseUrl}}/v1/regiones", tests=_test([
            "pm.test('200', () => pm.response.to.have.status(200));",
            "const b = pm.response.json();",
            "pm.test('total == len(data)', () => pm.expect(b.total).to.eql(b.data.length));",
            "pm.test('16 regiones', () => pm.expect(b.total).to.eql(16));",
        ])),
        req("REG-002 sin token", "GET", "{{baseUrl}}/v1/regiones", auth=False, tests=status_test(401)),
        req("REG-007 POST (metodo)", "POST", "{{baseUrl}}/v1/regiones", body={}, tests=status_test(405)),
    ])
    comunas = folder("05 - Comunas", [
        req("COM-001 happy region 13", "GET", "{{baseUrl}}/v1/regiones/13/comunas", tests=_test([
            "pm.test('200', () => pm.response.to.have.status(200));",
            "const b = pm.response.json();",
            "pm.test('region.id == 13', () => pm.expect(b.data.region.id).to.eql(13));",
            "pm.test('comunas prefijo 13', () => b.data.comunas.forEach(c => pm.expect(String(c.id)).to.match(/^13/)));",
        ])),
        req("COM-008 region inexistente", "GET", "{{baseUrl}}/v1/regiones/99/comunas", tests=status_test(404)),
        req("COM-010 region negativa", "GET", "{{baseUrl}}/v1/regiones/-1/comunas", tests=status_test(400, 404)),
        req("COM-012 region string", "GET", "{{baseUrl}}/v1/regiones/abc/comunas", tests=status_test(400)),
        req("COM-018 SQLi", "GET", "{{baseUrl}}/v1/regiones/13 OR 1=1/comunas", tests=status_test(400, 404)),
    ])
    rubros = folder("06 - Rubros", [
        req("RUB-001 happy", "GET", "{{baseUrl}}/v1/rubros", tests=status_test(200)),
        req("RUB-auth sin token", "GET", "{{baseUrl}}/v1/rubros", auth=False, tests=status_test(401)),
    ])
    actecos = folder("07 - Actecos", [
        req("ACT-001 happy rubro 7", "GET", "{{baseUrl}}/v1/rubros/7/acteco", tests=status_test(200)),
        req("ACT-008 rubro inexistente", "GET", "{{baseUrl}}/v1/rubros/99/acteco", tests=status_test(404)),
        req("ACT-invalid string", "GET", "{{baseUrl}}/v1/rubros/abc/acteco", tests=status_test(400)),
    ])
    apppos = folder("08 - App POS (sin JWT)", [
        req("APPC-001 app/regiones sin token", "GET", "{{baseUrl}}/v1/app/regiones", auth=False,
            tests=status_test(200, 401)),
        req("APPC app/comunas sin token", "GET", "{{baseUrl}}/v1/app/regiones/13/comunas", auth=False,
            tests=status_test(200, 401)),
        req("APPC app/rubros sin token", "GET", "{{baseUrl}}/v1/app/rubros", auth=False, tests=status_test(200, 401)),
        req("APPF-001 app/factura 33 sin token", "POST", "{{baseUrl}}/v1/app/factura", auth=False,
            body=F33, tests=status_test(200, 401)),
        req("APPF-009 app/factura otro rutEmisor", "POST", "{{baseUrl}}/v1/app/factura", auth=False,
            body=_mut(F33, "rutEmisor", "77151256-9"), tests=status_test(400, 401, 403)),
    ])
    consulta = folder("09 - Consultas (evidencia)", [
        req("Consulta DTE 33 por folio", "POST", "{{baseUrlConsultas}}/v1/app/dte/33/{{folioFactura}}",
            body={"rutEmisor": "10471336-K"}, tests=status_test(200, 404, 403)),
    ])

    return folder("QA", [login, f33, f34, nc, regiones, comunas, rubros, actecos, apppos, consulta])


def build_dev():
    return folder("DEV", [{"name": "Estructura preparada - NO EJECUTAR en Fase 1",
                           "item": [req("Login DEV", "POST",
                                        "https://apidev.mcdesaqa.cl/public/auth/web/v1/login",
                                        auth=False, body={"user": "{{loginUser}}", "pass": "{{loginPass}}"})]}])


def collection():
    return {
        "info": {"_postman_id": str(uuid.uuid4()), "name": "DTE API Testing",
                 "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "item": [build_qa(), build_dev()],
        "variable": [
            {"key": "baseUrl", "value": "{{baseUrlQA}}"},
            {"key": "jwt", "value": ""},
            {"key": "rutEmisor", "value": "10471336-K"},
            {"key": "rutReceptor", "value": "26461274-8"},
            {"key": "folioFactura", "value": ""},
        ],
    }


def environment(name, base, base_nc, base_cons, user, pw):
    return {
        "name": f"DTE API Testing - {name}",
        "values": [
            {"key": "baseUrlQA", "value": "https://apiqa-cloud.mcdesaqa.cl/central/dte/fe/recepcion", "enabled": True},
            {"key": "baseUrl", "value": base, "enabled": True},
            {"key": "baseUrlNc", "value": base_nc, "enabled": True},
            {"key": "baseUrlConsultas", "value": base_cons, "enabled": True},
            {"key": "loginUser", "value": user, "enabled": True},
            {"key": "loginPass", "value": pw, "type": "secret", "enabled": True},
            {"key": "rutEmisor", "value": user, "enabled": True},
            {"key": "rutReceptor", "value": "26461274-8", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
    }


DUMMYS_BASE = "https://5nnpwr8b-3000.brs.devtunnels.ms/central/dte/fe"


def write_dummys_env():
    """APIs mock: solo sirven las requests del canal App (/v1/app/*); no hay login."""
    (OUT / "DTE API Testing - DUMMYS.postman_environment.json").write_text(json.dumps(environment(
        "DUMMYS", f"{DUMMYS_BASE}/recepcion", f"{DUMMYS_BASE}/recepcion-nc",
        f"{DUMMYS_BASE}/consultas", "10471336-K", ""), indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    (OUT / "DTE API Testing.postman_collection.json").write_text(
        json.dumps(collection(), indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "DTE API Testing - QA.postman_environment.json").write_text(json.dumps(environment(
        "QA", "https://apiqa-cloud.mcdesaqa.cl/central/dte/fe/recepcion",
        "https://apiqa-cloud.mcdesaqa.cl/central/dte/fe/recepcion-nc",
        "https://apiqa-cloud.mcdesaqa.cl/central/dte/fe/consultas", "10471336-K", "1555"),
        indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "DTE API Testing - DEV.postman_environment.json").write_text(json.dumps(environment(
        "DEV", "https://apidev-cloud.mcdesaqa.cl/central/dte/fe/recepcion",
        "https://apidev-cloud.mcdesaqa.cl/central/dte/fe/recepcion-nc",
        "https://apidev-cloud.mcdesaqa.cl/central/dte/fe/consultas", "", ""),
        indent=2, ensure_ascii=False), encoding="utf-8")
    write_dummys_env()
    print("Postman collection + environments generados en", OUT)


if __name__ == "__main__":
    main()
