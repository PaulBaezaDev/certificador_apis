"""Consolida reports/evidence/*.json en un resumen legible + matriz CSV/MD."""
import csv
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config.environments import reports_dir  # noqa: E402  (ENV=DUMMYS -> reports/dummys/)

REPORTS = reports_dir()
EVID = REPORTS / "evidence"
OUT_MD = REPORTS / "resumen_ejecucion.md"


def load():
    rows = []
    for f in sorted(EVID.glob("*.json")):
        if f.name == "emitidos.csv":
            continue
        try:
            rows.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return rows


def main():
    rows = load()
    by_estado = Counter(r["estado"] for r in rows)
    by_api = Counter(r["api"] for r in rows)
    fails = [r for r in rows if r["estado"] == "FAIL"]
    blocked = [r for r in rows if r["estado"] == "BLOCKED"]

    emit_csv = EVID / "emitidos.csv"
    n_dte = 0
    if emit_csv.exists():
        n_dte = sum(1 for _ in csv.DictReader(emit_csv.open(encoding="utf-8")))

    lines = ["# Resumen de ejecucion", "",
             f"- Total casos con evidencia: **{len(rows)}**",
             f"- PASS: **{by_estado.get('PASS', 0)}**  |  FAIL: **{by_estado.get('FAIL', 0)}**  "
             f"|  BLOCKED: **{by_estado.get('BLOCKED', 0)}**",
             f"- DTE reales emitidos en QA: **{n_dte}**", "",
             "## Por API/suite", "", "| Suite | Casos |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(by_api.items())]
    lines += ["", "## FAIL / posibles defectos", "",
              "| ID | API | HTTP | Real | Nota |", "|---|---|---|---|---|"]
    for r in sorted(fails, key=lambda x: x["test_id"]):
        lines.append(f"| {r['test_id']} | {r['api']} | {r['http']} | "
                     f"{r['resultado_real']} | {r['nota'][:120]} |")
    lines += ["", "## BLOCKED", "", "| ID | Motivo |", "|---|---|"]
    for r in sorted(blocked, key=lambda x: x["test_id"]):
        lines.append(f"| {r['test_id']} | {r['nota'][:150]} |")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Resumen -> {OUT_MD}")
    print(f"PASS={by_estado.get('PASS',0)} FAIL={by_estado.get('FAIL',0)} "
          f"BLOCKED={by_estado.get('BLOCKED',0)} DTE={n_dte}")


if __name__ == "__main__":
    main()
