"""Registro de evidencia por caso + resultados para la matriz."""
import csv
import datetime
import json
import pathlib
import re

from config.environments import reports_dir

_REPORTS = reports_dir()
_EVID = _REPORTS / "evidence"
_MATRIZ = _REPORTS / "matriz_resultados.csv"
_rows = []


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)[:150]


def record(*, test_id, api, metodo, escenario, datos, esperado, res, prioridad, estado, nota=""):
    _EVID.mkdir(parents=True, exist_ok=True)
    real = ""
    if res is not None:
        real = f"codigoRespuesta={res.codigo_respuesta} mensaje={res.mensaje_respuesta}".strip()
    http = res.status if res is not None else ""
    payload = {
        "test_id": test_id, "api": api, "metodo": metodo, "escenario": escenario,
        "datos": datos, "resultado_esperado": esperado, "resultado_real": real,
        "http": http, "estado": estado, "prioridad": prioridad, "nota": nota,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "exchange": res.to_evidence() if res is not None else None,
    }
    (_EVID / f"{_slug(test_id)}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _rows.append({
        "ID": test_id, "API": api, "Metodo": metodo, "Escenario": escenario, "Datos": datos,
        "Resultado esperado": esperado, "Resultado real": real, "HTTP": http,
        "Estado": estado, "Prioridad": prioridad, "Nota": nota,
    })


def flush():
    if not _rows:
        return
    _REPORTS.mkdir(parents=True, exist_ok=True)
    with _MATRIZ.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(_rows[0].keys()))
        w.writeheader()
        w.writerows(sorted(_rows, key=lambda r: r["ID"]))
