"""Suite DUP - duplicidad / idempotencia / concurrencia (CRITICAL).

Consume folios reales. Tope local: <=10 DTE. Concurrencia <= 5 hilos.
"""
import concurrent.futures as cf

import pytest

from utils import assertions as a
from utils.api_client import ApiClient
from utils.payloads import factura33

FE = "/v1/factura"


@pytest.mark.duplicidad
@pytest.mark.emision
@pytest.mark.case_id("DUP-001")
def test_reenvio_x2_secuencial(client, env, token, budget):
    """Mismo payload 2 veces (secuencial): documentar si genera 2 folios / mismo / 409."""
    budget.check()
    p = factura33()
    r1 = client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=p)
    budget.maybe_record("DUP-001-a", r1, FE)
    budget.check()
    r2 = client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=p)
    budget.maybe_record("DUP-001-b", r2, FE)
    a.status_in(r1, 200)
    f1 = r1.json["datosDTE"]["folio"]
    if r2.status == 200:
        f2 = r2.json["datosDTE"]["folio"]
        assert f2 != f1, "IDEMPOTENCIA: devolvio el mismo folio (posible control anti-duplicado)"
        pytest.fail(f"POSIBLE DEFECTO: reenvio identico genero 2 DTE distintos ({f1}, {f2})")
    else:
        a.status_in(r2, 409, 422)  # habria mecanismo anti-duplicado


@pytest.mark.duplicidad
@pytest.mark.emision
@pytest.mark.case_id("DUP-002")
def test_reenvio_x3_secuencial(client, env, token, budget):
    """Mismo payload 3 veces: contar folios generados."""
    p = factura33(items=[{"numeroLinea": 1, "nombreItem": "Dup x3", "cantidad": 1,
                          "precioUnitarioNeto": 100000, "monto": 100000}])
    folios = []
    for i in range(3):
        budget.check()
        r = client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=p)
        budget.maybe_record(f"DUP-002-{i}", r, FE)
        if r.status == 200:
            folios.append(r.json["datosDTE"]["folio"])
    assert len(set(folios)) <= 3
    if len(set(folios)) == 3:
        pytest.fail(f"POSIBLE DEFECTO: 3 reenvios identicos -> 3 DTE ({folios})")


@pytest.mark.duplicidad
@pytest.mark.emision
@pytest.mark.case_id("DUP-003")
def test_rafaga_concurrente_x5(env, token, budget):
    """5 requests concurrentes con payload identico: ¿5 DTE? ¿lock? ¿idempotencia?"""
    for _ in range(5):
        budget.check()
    p = factura33(items=[{"numeroLinea": 1, "nombreItem": "Concurrencia x5", "cantidad": 1,
                          "precioUnitarioNeto": 100000, "monto": 100000}])

    def _emit(_):
        return ApiClient().post(f"{env['base_recepcion']}{FE}", token=token, json_body=p)

    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        resultados = list(ex.map(_emit, range(5)))

    folios, otros = [], []
    for r in resultados:
        if r.status == 200 and r.codigo_respuesta == "01":
            folio = r.json["datosDTE"]["folio"]
            folios.append(folio)
            budget.record("DUP-003", FE, 33, folio, "01")
        else:
            otros.append(r.status)
    resumen = f"200/folios={folios} otros={otros}"
    assert resultados, resumen
    if len(set(folios)) == 5:
        pytest.fail(f"POSIBLE DEFECTO: 5 concurrentes identicos -> 5 DTE. {resumen}")


@pytest.mark.duplicidad
@pytest.mark.emision
@pytest.mark.case_id("DUP-004")
def test_idempotency_key_header(client, env, token, budget):
    """Enviar Idempotency-Key: ¿tiene efecto anti-duplicado?"""
    budget.check()
    p = factura33(items=[{"numeroLinea": 1, "nombreItem": "IdemKey", "cantidad": 1,
                          "precioUnitarioNeto": 100000, "monto": 100000}])
    h = {"Idempotency-Key": "qa-dup-001", "X-Request-Id": "qa-dup-001"}
    r1 = client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=p, headers=h)
    budget.maybe_record("DUP-004-a", r1, FE)
    budget.check()
    r2 = client.post(f"{env['base_recepcion']}{FE}", token=token, json_body=p, headers=h)
    emitido2 = budget.maybe_record("DUP-004-b", r2, FE)
    a.status_in(r1, 200)
    if r2.status == 200 and emitido2:
        f1, f2 = r1.json["datosDTE"]["folio"], r2.json["datosDTE"]["folio"]
        # documenta: si f1==f2 hay idempotencia por header; si no, el header se ignora
        assert True, f"folios: {f1} / {f2}"


@pytest.mark.duplicidad
@pytest.mark.case_id("DUP-007")
def test_folios_correlativos(client, env, token):
    """Los folios emitidos en la corrida deben ser correlativos y sin saltos raros."""
    import csv
    import pathlib
    csvp = pathlib.Path(__file__).resolve().parent.parent / "reports" / "evidence" / "emitidos.csv"
    if not csvp.exists():
        pytest.skip("aun no hay DTE emitidos")
    folios = sorted({int(row["folio"]) for row in csv.DictReader(csvp.open(encoding="utf-8"))
                     if row["folio"].isdigit() and row["tipoDte"] == "33"})
    if len(folios) < 3:
        pytest.skip("pocos folios para evaluar correlatividad")
    saltos = [(folios[i], folios[i + 1]) for i in range(len(folios) - 1)
              if folios[i + 1] - folios[i] > 5]
    assert not saltos, f"saltos de folio > 5: {saltos}"
