"""Proxy CORS mínimo para el Certificador (sin dependencias, stdlib).

Uso:
    python proxy.py            # escucha en http://localhost:8787
    python proxy.py 9000       # otro puerto

Luego en el Certificador, campo "Proxy CORS":  http://localhost:8787

El navegador bloquea las llamadas directas a *.mcdesaqa.cl por CORS.
Este proxy reenvía la request tal cual (método, headers, body) y agrega
los headers Access-Control-* para que el navegador acepte la respuesta.
No modifica payloads ni respuestas.
"""
import sys
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
ALLOW_HOSTS = ("mcdesaqa.cl", "multicaja.cl", "klap.cl")
HOP = {"host", "content-length", "connection", "accept-encoding"}


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization,Content-Type,WL,Idempotency-Key,X-Request-Id")
        self.send_header("Access-Control-Max-Age", "86400")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _forward(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/proxy":
            self.send_response(404); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"usar /proxy?url=..."}')
            return
        target = urllib.parse.parse_qs(parsed.query).get("url", [None])[0]
        if not target or not any(h in urllib.parse.urlparse(target).netloc for h in ALLOW_HOSTS):
            self.send_response(400); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"url ausente o host no permitido"}')
            return

        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else None
        req = urllib.request.Request(target, data=body, method=self.command)
        for k, v in self.headers.items():
            if k.lower() not in HOP:
                req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
                status, headers = resp.status, resp.headers
        except urllib.error.HTTPError as e:
            data = e.read()
            status, headers = e.code, e.headers
        except Exception as e:  # noqa: BLE001
            self.send_response(502); self._cors(); self.end_headers()
            self.wfile.write(f'{{"error":"proxy: {e}"}}'.encode())
            return

        self.send_response(status)
        ct = headers.get("Content-Type", "application/json")
        self.send_header("Content-Type", ct)
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _forward

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[proxy] {self.command} {self.path.split('url=')[-1][:90]} -> {args[1] if len(args) > 1 else ''}\n")


if __name__ == "__main__":
    print(f"Proxy CORS escuchando en http://localhost:{PORT}  (Ctrl+C para salir)")
    print(f"En el Certificador, campo 'Proxy CORS':  http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
