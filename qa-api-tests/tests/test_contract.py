"""Suite CTR - contrato transversal de respuestas."""
import pytest

from utils import assertions as a


@pytest.mark.case_id("CTR-001")
def test_errores_traen_codigo_y_mensaje(client, token, env):
    """Toda respuesta de error de catalogo trae codigoRespuesta + mensajeRespuesta."""
    r = client.get(f"{env['base_recepcion']}/v1/regiones/99/comunas", token=token)
    a.is_json_object(r)
    a.tiene_campos(r.json, "codigoRespuesta", "mensajeRespuesta")


@pytest.mark.case_id("CTR-003")
@pytest.mark.seguridad
def test_5xx_no_exponen_stacktrace(client, token, env):
    """Forzar errores conocidos y verificar que 4xx/5xx no filtran detalle interno."""
    urls = [
        f"{env['base_recepcion']}/v1/factura",                   # GET -> 500 conocido
        f"{env['base_recepcion']}/v1/regiones/abc/comunas",
    ]
    fugas = []
    # consulta DTE (POST) con folio ajeno/inexistente
    consulta = client.post(f"{env['base_consultas']}/v1/app/dte/33/1", token=token,
                           json_body={"rutEmisor": env["user"]})
    resp = [(f"{env['base_consultas']}/v1/app/dte/33/1", consulta)]
    for u in urls:
        resp.append((u, client.get(u, token=token)))
    for u, r in resp:
        try:
            a.sin_stacktrace(r)
        except AssertionError as e:
            fugas.append((u, str(e)[:120]))
    assert not fugas, f"respuestas con posible fuga: {fugas}"


@pytest.mark.case_id("CTR-004")
def test_content_type_json(client, token, env):
    """Content-Type de respuesta siempre application/json."""
    r = client.get(f"{env['base_recepcion']}/v1/regiones", token=token)
    assert "application/json" in r.headers.get("Content-Type", "")


@pytest.mark.case_id("CTR-005")
def test_header_correlacion(client, token, env):
    """Debe existir algun header de correlacion para soporte (x-amzn-requestid / trace)."""
    r = client.get(f"{env['base_recepcion']}/v1/regiones", token=token)
    corr = [k for k in r.headers if k.lower() in
            ("x-amzn-requestid", "x-amzn-trace-id", "x-request-id", "x-correlation-id", "traceid")]
    assert corr, f"sin header de correlacion. headers: {list(r.headers)}"
