import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from config.environments import current, env_name, is_mock, reports_dir, DTE_BUDGET  # noqa: E402
from utils.api_client import ApiClient  # noqa: E402
from utils.auth import get_token  # noqa: E402
from utils.dte_budget import DteBudget  # noqa: E402
from utils import evidence  # noqa: E402
from utils.payloads import factura33, factura34  # noqa: E402


def pytest_addoption(parser):
    parser.addoption("--dte-budget", action="store", default=None,
                     help="Tope de DTE a emitir en QA (override de DTE_BUDGET del .env)")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    # DUMMYS escribe su reporte aparte para no pisar el de QA (reports/report.html)
    if env_name() == "DUMMYS" and getattr(config.option, "htmlpath", None):
        config.option.htmlpath = str(reports_dir() / "report.html")


def pytest_collection_modifyitems(config, items):
    """QA: omite la suite 'dummys'. DUMMYS: solo corre canal App + 'dummys' (el mock no tiene
    login, rutas con JWT ni el resto de endpoints)."""
    mock = is_mock()
    skip_qa = pytest.mark.skip(reason="suite exclusiva de ENV=DUMMYS")
    skip_mock = pytest.mark.skip(reason="ENV=DUMMYS: el mock solo expone el canal App (/v1/app/*) + health")
    for item in items:
        marks = {m.name for m in item.iter_markers()}
        if not mock and "dummys" in marks:
            item.add_marker(skip_qa)
        elif mock and not marks & {"app", "dummys"}:
            item.add_marker(skip_mock)


@pytest.fixture(scope="session")
def env():
    return current()


@pytest.fixture(scope="session")
def budget(request):
    limit = request.config.getoption("--dte-budget")
    return DteBudget(int(limit) if limit is not None else DTE_BUDGET)


@pytest.fixture(scope="session")
def token():
    from utils.auth import TokenCapExceeded
    if is_mock():
        pytest.skip("ENV=DUMMYS: el mock no tiene login ni valida JWT")
    try:
        return get_token()
    except TokenCapExceeded as e:
        pytest.skip(f"Auth QA no disponible (code 88: {e}). "
                    f"Definir QA_TOKEN en .env con un JWT vigente para ejecutar.")


@pytest.fixture()
def client():
    return ApiClient()


def _case_id(item):
    m = item.get_closest_marker("case_id")
    return m.args[0] if m else item.name


def _guess_api(nodeid: str) -> str:
    n = nodeid.lower()
    for key in ("notacredito", "factura33", "factura34", "app_factura", "app_catalogos",
                "comunas", "regiones", "acteco", "rubros", "consistencia", "auth",
                "duplicidad", "performance", "contract"):
        if key in n:
            return key
    return "?"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(autouse=True)
def _auto_evidence(request):
    """Una fila de matriz + un JSON de evidencia por test, aunque falle."""
    yield
    node = request.node
    setup_rep = getattr(node, "rep_setup", None)
    call_rep = getattr(node, "rep_call", None)
    estado, nota = "PASS", ""
    if setup_rep is not None and setup_rep.skipped:
        estado, nota = "BLOCKED", "skipped en setup"
    elif setup_rep is not None and setup_rep.failed:
        estado, nota = "FAIL", "error en setup"
    elif call_rep is not None:
        if call_rep.failed:
            estado = "FAIL"
            nota = (str(call_rep.longrepr).strip().splitlines() or [""])[-1][:300]
        elif call_rep.skipped:
            estado = "BLOCKED"
            nota = "skipped"
    elif call_rep is None:
        return

    client = request.node.funcargs.get("client")
    res = getattr(client, "last", None) if client else None
    marks = [m.name for m in node.iter_markers()]
    if "emision" in marks or "nc" in marks:
        prio = "CRITICAL"
    elif "seguridad" in marks:
        prio = "HIGH"
    elif "perf" in marks:
        prio = "LOW"
    else:
        prio = "MEDIUM"
    doc = (request.function.__doc__ or "").strip().splitlines()
    esperado = doc[0] if doc else "ver matriz 02"
    evidence.record(test_id=_case_id(node), api=_guess_api(node.nodeid),
                    metodo=getattr(res, "method", ""), escenario=node.name,
                    datos="", esperado=esperado, res=res, prioridad=prio,
                    estado=estado, nota=nota)


def pytest_sessionfinish(session, exitstatus):
    evidence.flush()


# ---- baseline de emision reutilizable ----

def _emit(env, token, budget, payload, tag):
    budget.check()
    c = ApiClient()
    res = c.post(f"{env['base_recepcion']}/v1/factura", token=token, json_body=payload)
    budget.maybe_record(tag, res, "/v1/factura")
    if not (res.status == 200 and res.codigo_respuesta == "01"):
        pytest.skip(f"No se pudo emitir baseline {tag}: HTTP {res.status} {res.text[:200]}")
    return {"payload": payload, "res": res, "folio": res.json["datosDTE"]["folio"],
            "tipo": res.json["datosDTE"]["tipoDte"]}


@pytest.fixture(scope="session")
def emitted_f33(env, token, budget):
    return _emit(env, token, budget, factura33(), "SESSION-emitted_f33")


@pytest.fixture(scope="session")
def emitted_f34(env, token, budget):
    return _emit(env, token, budget, factura34(), "SESSION-emitted_f34")
