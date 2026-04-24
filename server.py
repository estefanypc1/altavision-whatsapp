#!/usr/bin/env python3
"""
Dev server local — corre en http://localhost:8080
Uso: python3 server.py
"""
import os, sys, json, importlib.util
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).parent

def load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env()

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css":  "text/css",
    ".js":   "application/javascript",
    ".json": "application/json",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".svg":  "image/svg+xml",
    ".ico":  "image/x-icon",
}

def load_api_handler(name: str):
    path = ROOT / "api" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.handler

API_ROUTES = {
    "/api/whatsapp":    "whatsapp",
    "/api/chat":        "chat",
    "/api/appointments":"appointments",
}

class DevHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path} → {args[1]}")

    def _serve_api(self, module_name):
        HandlerClass = load_api_handler(module_name)
        HandlerClass.server  = self.server
        HandlerClass.headers = self.headers
        HandlerClass.rfile   = self.rfile
        HandlerClass.wfile   = self.wfile
        HandlerClass.request = self.request
        inst = HandlerClass.__new__(HandlerClass)
        inst.server  = self.server
        inst.client_address = self.client_address
        inst.headers = self.headers
        inst.rfile   = self.rfile
        inst.wfile   = self.wfile
        inst.request = self.request
        inst.requestline = self.requestline
        getattr(inst, f"do_{self.command}")()

    def _serve_static(self, path: str):
        if path == "/" or path == "":
            path = "/index.html"
        file_path = ROOT / path.lstrip("/")
        if not file_path.exists() or not file_path.is_file():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return
        mime = MIME.get(file_path.suffix, "application/octet-stream")
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _route(self):
        clean = self.path.split("?")[0]
        for route, module in API_ROUTES.items():
            if clean == route or clean == route + "/":
                self._serve_api(module)
                return
        self._serve_static(clean)

    def do_GET(self):    self._route()
    def do_POST(self):   self._route()
    def do_PATCH(self):  self._route()
    def do_OPTIONS(self):self._route()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"\n🌐 Alta Visión Dev Server")
    print(f"   http://localhost:{port}")
    print(f"   http://localhost:{port}/dashboard.html")
    print(f"\n   Ctrl+C para detener\n")
    HTTPServer(("", port), DevHandler).serve_forever()
