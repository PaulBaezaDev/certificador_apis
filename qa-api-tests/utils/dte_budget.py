"""Guard de presupuesto de DTE emitidos en QA. Impide superar el tope pactado."""
import csv
import datetime
import pathlib
import threading

_LOCK = threading.Lock()
from config.environments import reports_dir

_EVID = reports_dir() / "evidence"
_CSV = _EVID / "emitidos.csv"


class BudgetExceeded(Exception):
    pass


class DteBudget:
    def __init__(self, limit: int):
        self.limit = limit
        self.count = 0
        _EVID.mkdir(parents=True, exist_ok=True)
        if not _CSV.exists():
            with _CSV.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["timestamp", "test_id", "endpoint", "tipoDte", "folio", "codigoRespuesta"])

    def check(self):
        """Si se alcanzo el tope, se OMITE el caso (skip) en vez de fallarlo."""
        import pytest
        with _LOCK:
            over = self.count >= self.limit
        if over:
            pytest.skip(f"Tope de {self.limit} DTE alcanzado; caso omitido para no emitir mas en QA.")

    def record(self, test_id: str, endpoint: str, tipo_dte, folio, codigo):
        with _LOCK:
            self.count += 1
            with _CSV.open("a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    datetime.datetime.now().isoformat(timespec="seconds"),
                    test_id, endpoint, tipo_dte, folio, codigo,
                ])

    def maybe_record(self, test_id: str, res, endpoint: str):
        """Registra si la respuesta indica emision exitosa (200 + codigoRespuesta 01)."""
        if res.status == 200 and res.codigo_respuesta == "01":
            datos = (res.json or {}).get("datosDTE") or {}
            self.record(test_id, endpoint, datos.get("tipoDte"), datos.get("folio"), res.codigo_respuesta)
            return True
        return False
