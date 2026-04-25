import os, json, uuid, base64, urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timedelta

OPENAI_API_KEY     = os.environ.get("OPENAI_API_KEY", "")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_NUMBER         = "+12136957012"
MESSAGING_SERVICE_SID = "MG719d8d8e733527783215cf41dbe7ec9e"  # altavision
BOT_NAME              = "Clarivista"
APPOINTMENTS_FILE  = "/tmp/altavision_appointments.json"

DAYS_ES = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado",
}
MONTHS_ES = {
    "January": "enero", "February": "febrero", "March": "marzo",
    "April": "abril", "May": "mayo", "June": "junio",
    "July": "julio", "August": "agosto", "September": "septiembre",
    "October": "octubre", "November": "noviembre", "December": "diciembre",
}

# In-memory sessions: phone -> {history, privacy_accepted}
sessions: dict = {}

PRIVACY_NOTICE = (
    "👁️ *Alta Visión — Aviso de Privacidad*\n\n"
    "Al continuar, autorizas el tratamiento de tus datos personales conforme "
    "a la *Ley 1581 de 2012* (Habeas Data - Colombia). Tus datos se usarán "
    "únicamente para gestión de citas y comunicaciones de salud visual.\n\n"
    "Para ejercer tus derechos escribe a: educacion@altavision.com.co\n\n"
    "_Continúa escribiendo para hablar con Clarivista ✨_"
)

SYSTEM_PROMPT = """Eres Clarivista, asistente virtual de Alta Visión, clínica oftalmológica en Bogotá, Colombia.

MISIÓN: Informar sobre servicios, agendar citas y orientar en salud visual con calidez y profesionalismo.

ALTA VISIÓN:
• Dirección: Carrera 14 No. 86a-15, Bogotá
• Tel: 6164585 opción 5 | Email: educacion@altavision.com.co
• Horario: Lunes-Viernes 8:00 AM – 6:00 PM | Sábados 8:00 AM – 12:00 PM
• Facebook: facebook.com/hablemosdesalud.com.co

SERVICIOS:
1. Valoración Oftalmológica 360° — Examen completo de la visión
2. Diagnóstico Oftalmológico — Detección temprana de enfermedades
3. Cirugía LASIK — Corrección definitiva de la visión
4. Adaptación de Lentes de Contacto y Gafas
5. Brigadas Empresariales de Salud Visual
6. Educación en Salud Visual

ESPECIALIDADES: Glaucoma, cataratas, estrabismo, miopía, hipermetropía, astigmatismo, ojo seco, degeneración macular, ambliopía.
EQUIPOS: OCT Optovue, Pentacam, Perímetro Humphrey, Lenstar.

AGENDAMIENTO DE CITAS:
Cuando el paciente quiera agendar, recopila paso a paso:
1. Nombre completo
2. Servicio o motivo de consulta
3. Fecha preferida (muéstrale las opciones disponibles del contexto)
4. Hora preferida

Una vez tengas TODOS los datos, confirma con el paciente mostrando un resumen.
Cuando el paciente confirme, incluye al FINAL de tu respuesta (en línea separada):
CITA_CONFIRMADA|nombre|servicio|fecha|hora

PERSONALIDAD: Cálida, profesional, empática. Español colombiano natural. Emojis moderados (👁️ 📅 ✅ 🏥).
REGLA IMPORTANTE: No hagas diagnósticos médicos. Recomienda siempre consultar con el oftalmólogo."""


def get_available_slots_text() -> str:
    slots = []
    days_added = 0
    d = datetime.now() + timedelta(days=1)
    while days_added < 5:
        wd = d.weekday()
        if wd <= 4:
            day_name = DAYS_ES[d.strftime("%A")]
            month_name = MONTHS_ES[d.strftime("%B")]
            slots.append(f"📅 {day_name} {d.day} de {month_name}: 8:00, 9:00, 10:00, 11:00 AM | 2:00, 3:00, 4:00, 5:00 PM")
            days_added += 1
        elif wd == 5:
            month_name = MONTHS_ES[d.strftime("%B")]
            slots.append(f"📅 Sábado {d.day} de {month_name}: 8:00, 9:00, 10:00, 11:00 AM")
            days_added += 1
        d += timedelta(days=1)
    return "\n".join(slots)


def load_appointments() -> list:
    try:
        with open(APPOINTMENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_appointment(appt: dict) -> None:
    appts = load_appointments()
    appts.append(appt)
    with open(APPOINTMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(appts, f, ensure_ascii=False, indent=2)


def _twilio_auth() -> str:
    return base64.b64encode(f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode()).decode()


def _auth_headers() -> dict:
    return {
        "Authorization": f"Basic {_twilio_auth()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


# ── Conversations API reply ───────────────────────────────────────────────────
def send_conversations_message(conversation_sid: str, body: str) -> None:
    url = f"https://conversations.twilio.com/v1/Conversations/{conversation_sid}/Messages"
    data = urllib.parse.urlencode({
        "Body": body,
        "Author": f"whatsapp:{TWILIO_NUMBER}",
    }).encode()
    req = urllib.request.Request(url, data=data, headers=_auth_headers())
    with urllib.request.urlopen(req, timeout=15) as r:
        r.read()


# ── Simple Messaging API reply (fallback) ─────────────────────────────────────
def send_twilio_message(to: str, body: str) -> None:
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    data = urllib.parse.urlencode({
        "MessagingServiceSid": MESSAGING_SERVICE_SID,
        "To":   f"whatsapp:{to}",
        "Body": body,
    }).encode()
    req = urllib.request.Request(url, data=data, headers=_auth_headers())
    with urllib.request.urlopen(req, timeout=15) as r:
        r.read()


def call_openai(messages: list) -> str:
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": messages,
        "max_tokens": 600,
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
    return result["choices"][0]["message"]["content"].strip()


def process_message(from_number: str, body: str, reply_fn) -> None:
    """Core logic: session management, OpenAI call, appointment extraction."""
    session = sessions.get(from_number, {"history": [], "privacy_accepted": False})

    if not session["privacy_accepted"]:
        session["privacy_accepted"] = True
        sessions[from_number] = session
        reply_fn(PRIVACY_NOTICE)

    slots_text = get_available_slots_text()
    system = SYSTEM_PROMPT + f"\n\nDISPONIBILIDAD ACTUAL:\n{slots_text}"

    session["history"].append({"role": "user", "content": body})
    messages = [{"role": "system", "content": system}] + session["history"][-20:]

    ai_response = call_openai(messages)

    if "CITA_CONFIRMADA|" in ai_response:
        try:
            raw = ai_response.split("CITA_CONFIRMADA|", 1)[1].strip()
            parts = [p.strip() for p in raw.split("|")]
            appt_id = str(uuid.uuid4())[:8].upper()
            appt = {
                "id": appt_id,
                "phone": from_number,
                "name":    parts[0] if len(parts) > 0 else "Paciente",
                "service": parts[1] if len(parts) > 1 else "Consulta",
                "date":    parts[2] if len(parts) > 2 else "",
                "time":    parts[3] if len(parts) > 3 else "",
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            }
            save_appointment(appt)
            ai_response = ai_response.split("CITA_CONFIRMADA|", 1)[0].strip()
            if not ai_response:
                ai_response = (
                    f"✅ ¡Cita confirmada, {appt['name']}!\n\n"
                    f"🔖 Código: *#{appt_id}*\n"
                    f"📋 {appt['service']}\n"
                    f"📅 {appt['date']} a las {appt['time']}\n\n"
                    "¡Te esperamos en Alta Visión! 👁️\n"
                    "_Carrera 14 No. 86a-15, Bogotá_"
                )
        except Exception:
            ai_response = ai_response.split("CITA_CONFIRMADA|", 1)[0].strip()

    session["history"].append({"role": "assistant", "content": ai_response})
    if len(session["history"]) > 40:
        session["history"] = session["history"][-40:]
    sessions[from_number] = session

    reply_fn(ai_response)


def _ok_response() -> bytes:
    return b'<?xml version="1.0"?><Response/>'


class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):  # noqa: A002
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Webhook activo - Alta Visión / Clarivista".encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        params = dict(urllib.parse.parse_qsl(raw))

        event_type = params.get("EventType", "")

        # ── Conversations API (WhatsApp Business) ─────────────────────────────
        if event_type == "onMessageAdded":
            author           = params.get("Author", "")
            body             = params.get("Body", "").strip()
            conversation_sid = params.get("ConversationSid", "")

            # Skip bot's own messages and empty bodies
            bot_ids = {
                f"whatsapp:{TWILIO_NUMBER}", TWILIO_NUMBER,
                BOT_NAME, BOT_NAME.lower(), "system",
            }
            if author in bot_ids or not body or not conversation_sid:
                self._send_ok()
                return

            from_number = author.replace("whatsapp:", "")
            reply_fn = lambda msg: send_conversations_message(conversation_sid, msg)

            try:
                process_message(from_number, body, reply_fn)
            except Exception as exc:
                print(f"[conversations] error: {exc}")
            self._send_ok()
            return

        # ── Simple Messaging API (SMS / Sandbox) ──────────────────────────────
        author   = params.get("ProfileName", "").strip()
        from_raw = params.get("From", "")
        body     = params.get("Body", "").strip()
        from_number = from_raw.replace("whatsapp:", "")

        skip = {TWILIO_NUMBER, f"whatsapp:{TWILIO_NUMBER}", BOT_NAME.lower(), BOT_NAME, "system"}
        if (author and author.lower() in {s.lower() for s in skip}) or not body:
            self._send_ok()
            return

        reply_fn = lambda msg: send_twilio_message(from_number, msg)
        try:
            process_message(from_number, body, reply_fn)
        except Exception as exc:
            print(f"[whatsapp] error: {exc}")

        self._send_ok()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def _send_ok(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.end_headers()
        self.wfile.write(_ok_response())
