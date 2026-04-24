import os, json, urllib.request
from http.server import BaseHTTPRequestHandler

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

SYSTEM_PROMPT = """Eres Clarivista, asistente virtual de Alta Visión, clínica oftalmológica en Bogotá, Colombia.

MISIÓN: Informar sobre servicios, orientar en agendamiento y resolver dudas de salud visual.

ALTA VISIÓN:
• Dirección: Carrera 14 No. 86a-15, Bogotá
• Tel: 6164585 opción 5 | Email: educacion@altavision.com.co
• Horario: Lunes-Viernes 8:00 AM – 6:00 PM | Sábados 8:00 AM – 12:00 PM

SERVICIOS: Valoración Oftalmológica 360°, Diagnóstico Oftalmológico, Cirugía LASIK,
Adaptación de Lentes de Contacto y Gafas, Brigadas Empresariales, Educación en Salud Visual.

ESPECIALIDADES: Glaucoma, cataratas, estrabismo, miopía, hipermetropía, astigmatismo,
ojo seco, degeneración macular, ambliopía.

PERSONALIDAD: Cálida, profesional, empática. Español colombiano. Emojis moderados (👁️ 📅 ✅).
REGLA: No hagas diagnósticos médicos. Siempre recomienda consultar con el oftalmólogo."""


class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):  # noqa: A002
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length))
        messages = data.get("messages", [])

        payload = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            "max_tokens": 500,
            "temperature": 0.75,
        }).encode()

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())

        reply = result["choices"][0]["message"]["content"].strip()

        body = json.dumps({"reply": reply}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()
