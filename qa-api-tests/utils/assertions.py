"""Aserciones reutilizables, alineadas al contrato documentado."""
import re

_STACK_HINTS = re.compile(
    r"(java\.[a-z]|org\.springframework|com\.klap|Exception:|at [a-zA-Z]+\.[a-zA-Z]+\("
    r"|SQLSTATE|psql:|SELECT .* FROM |Traceback|\.java:\d+)", re.I)


def status_in(res, *codes):
    assert res.status in codes, (
        f"HTTP esperado {codes}, real {res.status}. body={res.text[:500]}")


def is_json_object(res):
    assert isinstance(res.json, dict), f"Se esperaba objeto JSON, real: {res.text[:300]}"


def codigo_respuesta(res, *valores):
    is_json_object(res)
    assert res.codigo_respuesta in valores, (
        f"codigoRespuesta esperado {valores}, real {res.codigo_respuesta!r} "
        f"(mensaje={res.mensaje_respuesta!r})")


def sin_stacktrace(res):
    assert not _STACK_HINTS.search(res.text or ""), (
        f"La respuesta parece exponer detalle interno: {res.text[:400]}")


def tiene_campos(obj, *campos):
    faltan = [c for c in campos if c not in obj]
    assert not faltan, f"Faltan campos {faltan} en {list(obj)}"


def emitido_ok(res):
    status_in(res, 200)
    codigo_respuesta(res, "01")
    datos = res.json.get("datosDTE") or {}
    tiene_campos(datos, "tipoDte", "folio", "fechaEmision")
    assert datos.get("folio"), "folio vacio en emision exitosa"
    return datos
