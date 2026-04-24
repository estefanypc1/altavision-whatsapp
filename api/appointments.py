import os, json
from http.server import BaseHTTPRequestHandler

APPOINTMENTS_FILE = "/tmp/altavision_appointments.json"


def load_appointments() -> list:
    try:
        with open(APPOINTMENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_appointments(appts: list) -> None:
    with open(APPOINTMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(appts, f, ensure_ascii=False, indent=2)


class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):  # noqa: A002
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._json(load_appointments())

    def do_PATCH(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length))
        appt_id  = data.get("id")
        new_status = data.get("status")

        appts = load_appointments()
        updated = False
        for appt in appts:
            if appt.get("id") == appt_id:
                appt["status"] = new_status
                updated = True
                break
        if updated:
            save_appointments(appts)
        self._json({"ok": updated})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()
