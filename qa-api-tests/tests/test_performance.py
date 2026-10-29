"""Suite PERF - rendimiento controlado (opt-in: pytest -m perf). Solo GET de catalogos."""
import concurrent.futures as cf
import statistics as st

import pytest

from utils.api_client import ApiClient

pytestmark = pytest.mark.perf


def _pctl(vals, p):
    vals = sorted(vals)
    if not vals:
        return 0
    k = max(0, min(len(vals) - 1, int(round((p / 100) * (len(vals) - 1)))))
    return vals[k]


def _run_seq(url, token, n):
    lat, errs = [], 0
    c = ApiClient()
    for _ in range(n):
        r = c.get(url, token=token)
        lat.append(r.elapsed_ms)
        if r.status != 200:
            errs += 1
    return lat, errs


def _report(name, lat, errs, n):
    print(f"\n[PERF] {name} n={n} errores={errs} "
          f"media={st.mean(lat):.0f}ms p50={_pctl(lat,50)}ms "
          f"p95={_pctl(lat,95)}ms p99={_pctl(lat,99)}ms max={max(lat)}ms")


@pytest.mark.parametrize("n", [10, 50])
def test_regiones_secuencial(env, token, n):
    """GET /v1/regiones x10 y x50 secuencial: p50/p95/p99/max/errores."""
    lat, errs = _run_seq(f"{env['base_recepcion']}/v1/regiones", token, n)
    _report(f"GET /v1/regiones", lat, errs, n)
    assert errs == 0
    assert _pctl(lat, 95) < 4000


def test_comunas_secuencial(env, token):
    """GET /v1/regiones/13/comunas x50."""
    lat, errs = _run_seq(f"{env['base_recepcion']}/v1/regiones/13/comunas", token, 50)
    _report("GET comunas", lat, errs, 50)
    assert errs == 0


def test_acteco_secuencial(env, token):
    """GET /v1/rubros/7/acteco x50."""
    lat, errs = _run_seq(f"{env['base_recepcion']}/v1/rubros/7/acteco", token, 50)
    _report("GET acteco", lat, errs, 50)
    assert errs == 0


def test_regiones_concurrente(env, token):
    """GET /v1/regiones 5 hilos x10 (50 total): latencia bajo concurrencia leve."""
    url = f"{env['base_recepcion']}/v1/regiones"

    def _one(_):
        r = ApiClient().get(url, token=token)
        return r.elapsed_ms, r.status

    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        res = list(ex.map(_one, range(50)))
    lat = [x[0] for x in res]
    errs = sum(1 for x in res if x[1] != 200)
    _report("GET /v1/regiones (5 hilos)", lat, errs, 50)
    assert errs == 0


def test_rate_limiting(env, token):
    """30 GET en rafaga: detectar 429 / Retry-After."""
    url = f"{env['base_recepcion']}/v1/regiones"
    c = ApiClient()
    codes = [c.get(url, token=token).status for _ in range(30)]
    n429 = codes.count(429)
    print(f"\n[PERF] rafaga 30: codigos={sorted(set(codes))} 429s={n429}")
    # informativo: no falla, solo documenta si hay rate limiting
    assert all(x in (200, 429, 503) for x in codes), f"codigos inesperados: {set(codes)}"
