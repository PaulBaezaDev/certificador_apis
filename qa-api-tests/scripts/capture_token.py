"""Reintenta el login de QA hasta conseguir 1 token y lo guarda en .env como QA_TOKEN.

Uso: python scripts/capture_token.py [--max-min 240]
El cap de tokens del comercio libera cupos lentamente; este script se queda esperando
un cupo y, al obtenerlo, persiste el token para que la suite completa corra con UNO solo.
"""
import argparse
import pathlib
import sys
import time

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
URL = "https://apiqa.mcdesaqa.cl/public/auth/web/v1/login"
CREDS = {"user": "10471336-K", "pass": "1555"}


def try_login():
    try:
        r = requests.post(URL, json=CREDS, timeout=30)
        b = r.json()
    except Exception as e:  # noqa: BLE001
        return None, f"error: {e}"
    if b.get("code") == 1:
        return b["data"]["token"], "ok"
    return None, f"code {b.get('code')}: {b.get('message')}"


def write_env(token: str):
    lines = []
    if ENV.exists():
        lines = [ln for ln in ENV.read_text(encoding="utf-8").splitlines()
                 if not ln.startswith("QA_TOKEN=")]
    lines.append(f"QA_TOKEN={token}")
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-min", type=int, default=240)
    ap.add_argument("--interval", type=int, default=45)
    a = ap.parse_args()
    deadline = time.time() + a.max_min * 60
    n = 0
    while time.time() < deadline:
        n += 1
        tok, msg = try_login()
        if tok:
            write_env(tok)
            print(f"[capture_token] intento {n}: TOKEN OBTENIDO -> guardado en {ENV}")
            return 0
        print(f"[capture_token] intento {n}: {msg}", flush=True)
        time.sleep(a.interval)
    print("[capture_token] timeout sin obtener token", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
