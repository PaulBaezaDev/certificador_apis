"""Login y generacion de variantes de token para la suite AUTH.

Politica de token (el servicio de auth capa la cantidad de tokens por usuario, code 88):
  1. Si hay QA_TOKEN en .env y aun NO expiro (claim exp) -> se reutiliza, sin login.
  2. Si no hay o ya expiro -> se hace UN login y se PERSISTE en .env como QA_TOKEN
     para que las siguientes corridas lo reutilicen.
  3. Las variantes (expirado/manipulado/firma) se derivan del token en memoria, sin nuevos logins.
"""
import base64
import json
import os
import pathlib
import time

import requests

from config.environments import current

_ENV_FILE = pathlib.Path(__file__).resolve().parent.parent / ".env"


class TokenCapExceeded(RuntimeError):
    """Auth devuelve code 88 'Maximo de tokens excedido'."""


def login(user: str | None = None, password: str | None = None, alt: bool = False) -> dict:
    env = current()
    url = env["auth_url_alt"] if alt else env["auth_url"]
    r = requests.post(url, json={"user": user or env["user"], "pass": password or env["pass"]}, timeout=30)
    try:
        body = r.json()
    except ValueError:
        body = {}
    if body.get("code") == 88:
        raise TokenCapExceeded(body.get("message", "Maximo de tokens excedido"))
    r.raise_for_status()
    return body


_CACHE: dict[str, str] = {}


def _exp(token: str) -> int:
    try:
        return int(decode_payload(token).get("exp", 0))
    except Exception:  # noqa: BLE001
        return 0


def token_vigente(token: str, margen_seg: int = 120) -> bool:
    e = _exp(token)
    return e == 0 or e - margen_seg > time.time()


def _persist_env(token: str):
    try:
        lines = []
        if _ENV_FILE.exists():
            lines = [ln for ln in _ENV_FILE.read_text(encoding="utf-8").splitlines()
                     if not ln.startswith("QA_TOKEN=")]
        lines.append(f"QA_TOKEN={token}")
        _ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass


def get_token(force_new: bool = False, **kw) -> str:
    """Devuelve un token, reutilizando QA_TOKEN mientras siga vigente."""
    key = repr(sorted(kw.items()))
    if not force_new and key in _CACHE:
        return _CACHE[key]

    if not force_new and not kw:
        guardado = os.getenv("QA_TOKEN", "").strip()
        if guardado and token_vigente(guardado):
            _CACHE[key] = guardado
            return guardado

    try:
        tok = login(**kw)["data"]["token"]
        if not kw:
            _persist_env(tok)
            os.environ["QA_TOKEN"] = tok
        _CACHE[key] = tok
        return tok
    except TokenCapExceeded:
        fallback = os.getenv("QA_TOKEN", "").strip()
        if fallback:  # aunque este por vencer, es lo unico disponible
            _CACHE[key] = fallback
            return fallback
        raise


def _b64url_decode(seg: str) -> bytes:
    seg += "=" * (-len(seg) % 4)
    return base64.urlsafe_b64decode(seg)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def decode_payload(token: str) -> dict:
    return json.loads(_b64url_decode(token.split(".")[1]))


def tamper_payload(token: str, **changes) -> str:
    """Reescribe claims del payload SIN re-firmar (firma queda invalida)."""
    h, p, s = token.split(".")
    payload = json.loads(_b64url_decode(p))
    payload.update(changes)
    return f"{h}.{_b64url(json.dumps(payload).encode())}.{s}"


def expired_token(token: str) -> str:
    return tamper_payload(token, iat=1600000000, exp=1600003600)


def bad_signature(token: str) -> str:
    h, p, s = token.split(".")
    flipped = ("A" if s[-1] != "A" else "B")
    return f"{h}.{p}.{s[:-1]}{flipped}"


def malformed_two_segments(token: str) -> str:
    h, p, _ = token.split(".")
    return f"{h}.{p}"


def garbage_token() -> str:
    return "not-a-jwt-" + "x" * 20


def huge_token() -> str:
    return "eyJ" + "A" * 100_000
