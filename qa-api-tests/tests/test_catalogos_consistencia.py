"""Suite CONS - consistencia cross-endpoint de catalogos (prioridad HIGH)."""
import pytest

from utils import assertions as a


@pytest.fixture(scope="module")
def regiones(env):
    from utils.api_client import ApiClient
    from utils.auth import get_token
    return ApiClient().get(f"{env['base_recepcion']}/v1/regiones", token=get_token()).json["data"]


@pytest.mark.case_id("CONS-001")
def test_comuna_ids_globalmente_unicos(client, token, env, regiones):
    """id de comuna no colisiona entre regiones distintas."""
    vistos = {}
    colisiones = []
    for reg in regiones:
        r = client.get(f"{env['base_recepcion']}/v1/regiones/{reg['id']}/comunas", token=token)
        if r.status != 200:
            continue
        for c in r.json["data"]["comunas"]:
            if c["id"] in vistos and vistos[c["id"]] != reg["id"]:
                colisiones.append((c["id"], vistos[c["id"]], reg["id"]))
            vistos[c["id"]] = reg["id"]
    assert not colisiones, f"comuna id en >1 region: {colisiones[:10]}"


@pytest.mark.case_id("CONS-002")
def test_conteo_total_comunas(client, token, env, regiones):
    """La suma de comunas por region es coherente (Chile ~346)."""
    total = 0
    for reg in regiones:
        r = client.get(f"{env['base_recepcion']}/v1/regiones/{reg['id']}/comunas", token=token)
        if r.status == 200:
            total += r.json["total"]
    assert 300 <= total <= 360, f"total comunas pais fuera de rango esperado: {total}"


@pytest.mark.case_id("CONS-003")
def test_acteco_ids_globalmente_unicos(client, token, env):
    """acteco.id no colisiona entre rubros."""
    rubros = client.get(f"{env['base_recepcion']}/v1/rubros", token=token).json["data"]
    vistos = {}
    colisiones = []
    for rb in rubros:
        r = client.get(f"{env['base_recepcion']}/v1/rubros/{rb['id']}/acteco", token=token)
        if r.status != 200:
            continue
        for x in r.json["data"]["acteco"]:
            if x["id"] in vistos and vistos[x["id"]] != rb["id"]:
                colisiones.append((x["id"], vistos[x["id"]], rb["id"]))
            vistos[x["id"]] = rb["id"]
    assert not colisiones, f"acteco id en >1 rubro: {colisiones[:10]}"


@pytest.mark.case_id("CONS-004")
def test_codacteco_unicos(client, token, env):
    """codActeco (codigo SII) unico en todo el catalogo."""
    rubros = client.get(f"{env['base_recepcion']}/v1/rubros", token=token).json["data"]
    cods = []
    for rb in rubros:
        r = client.get(f"{env['base_recepcion']}/v1/rubros/{rb['id']}/acteco", token=token)
        if r.status == 200:
            cods += [x["codActeco"] for x in r.json["data"]["acteco"]]
    dups = {c for c in cods if cods.count(c) > 1}
    assert not dups, f"codActeco duplicados: {list(dups)[:10]}"
