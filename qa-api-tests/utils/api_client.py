"""Wrapper delgado sobre requests. Devuelve un resultado estructurado y trazable."""
import json
import time
from dataclasses import dataclass, field
from typing import Any

import requests

_SENSIBLE = ("authorization", "cookie", "set-cookie")


def _mask_headers(h: dict) -> dict:
    out = {}
    for k, v in (h or {}).items():
        if k.lower() in _SENSIBLE and isinstance(v, str) and len(v) > 16:
            out[k] = v[:12] + "...(masked)"
        else:
            out[k] = v
    return out


@dataclass
class ApiResult:
    method: str
    url: str
    status: int
    elapsed_ms: int
    req_headers: dict
    req_body: Any
    headers: dict
    text: str
    json: Any = None
    error: str | None = None

    @property
    def codigo_respuesta(self):
        return self.json.get("codigoRespuesta") if isinstance(self.json, dict) else None

    @property
    def mensaje_respuesta(self):
        return self.json.get("mensajeRespuesta") if isinstance(self.json, dict) else None

    def to_evidence(self) -> dict:
        return {
            "request": {
                "method": self.method,
                "url": self.url,
                "headers": _mask_headers(self.req_headers),
                "body": self.req_body,
            },
            "response": {
                "status": self.status,
                "elapsed_ms": self.elapsed_ms,
                "headers": dict(self.headers),
                "body": self.json if self.json is not None else self.text[:4000],
            },
            "error": self.error,
        }


class ApiClient:
    def __init__(self):
        self.session = requests.Session()
        self.last: ApiResult | None = None

    def request(self, method: str, url: str, *, token: str | None = None,
                headers: dict | None = None, json_body: Any = "__NONE__",
                raw_body: str | None = None, params: dict | None = None,
                timeout: int = 30) -> ApiResult:
        h = {"Accept": "application/json"}
        if headers:
            h.update(headers)
        if token is not None:
            h["Authorization"] = f"Bearer {token}"
        kwargs: dict = {"headers": h, "params": params, "timeout": timeout}
        body_repr: Any = None
        if raw_body is not None:
            kwargs["data"] = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
            body_repr = raw_body if isinstance(raw_body, str) else "<bytes>"
            h.setdefault("Content-Type", "application/json")
        elif json_body != "__NONE__":
            kwargs["json"] = json_body
            body_repr = json_body

        t0 = time.perf_counter()
        err = None
        try:
            r = self.session.request(method, url, **kwargs)
            elapsed = int((time.perf_counter() - t0) * 1000)
            try:
                parsed = r.json()
            except (ValueError, json.JSONDecodeError):
                parsed = None
            res = ApiResult(method, url, r.status_code, elapsed, dict(h), body_repr,
                            dict(r.headers), r.text, parsed)
        except requests.RequestException as e:
            elapsed = int((time.perf_counter() - t0) * 1000)
            err = f"{type(e).__name__}: {e}"
            res = ApiResult(method, url, -1, elapsed, dict(h), body_repr, {}, "", None, err)
        self.last = res
        return res

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)

    def put(self, url, **kw):
        return self.request("PUT", url, **kw)

    def patch(self, url, **kw):
        return self.request("PATCH", url, **kw)

    def delete(self, url, **kw):
        return self.request("DELETE", url, **kw)

    def options(self, url, **kw):
        return self.request("OPTIONS", url, **kw)

    def head(self, url, **kw):
        return self.request("HEAD", url, **kw)
