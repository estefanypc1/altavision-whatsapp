#!/usr/bin/env python3
"""
Configura automáticamente el webhook de Twilio para Alta Visión.
Uso: python3 configure_twilio.py https://tu-app.vercel.app
"""
import sys, os, json, base64, urllib.request, urllib.parse
from pathlib import Path

def load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

load_env()

ACCOUNT_SID   = os.environ.get("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN    = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_NUMBER = "+18106921979"

if len(sys.argv) < 2:
    print("Uso: python3 configure_twilio.py https://tu-app.vercel.app")
    sys.exit(1)

VERCEL_URL  = sys.argv[1].rstrip("/")
WEBHOOK_URL = f"{VERCEL_URL}/api/whatsapp"

def auth_header():
    return "Basic " + base64.b64encode(f"{ACCOUNT_SID}:{AUTH_TOKEN}".encode()).decode()

def api_call(url, data=None, method="GET"):
    req = urllib.request.Request(
        url, data=data,
        headers={"Authorization": auth_header(),
                 "Content-Type": "application/x-www-form-urlencoded"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

print(f"\n🔍 Buscando número {TWILIO_NUMBER}…")
encoded = urllib.parse.quote(TWILIO_NUMBER)
result  = api_call(
    f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}"
    f"/IncomingPhoneNumbers.json?PhoneNumber={encoded}"
)
numbers = result.get("incoming_phone_numbers", [])

if not numbers:
    print(f"\n❌ Número {TWILIO_NUMBER} no encontrado en la cuenta Twilio.")
    print("\n👉 Configura el webhook manualmente:")
    print("   Twilio Console → Phone Numbers → Manage → número")
    print(f"   → Messaging → Webhook URL → {WEBHOOK_URL}")
    sys.exit(1)

sid = numbers[0]["sid"]
print(f"✅ Número encontrado: SID {sid}")

print(f"🔧 Configurando webhook → {WEBHOOK_URL}")
data = urllib.parse.urlencode({
    "SmsUrl":             WEBHOOK_URL,
    "SmsMethod":          "POST",
    "SmsFallbackUrl":     WEBHOOK_URL,
    "SmsFallbackMethod":  "POST",
}).encode()

updated = api_call(
    f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}"
    f"/IncomingPhoneNumbers/{sid}.json",
    data=data, method="POST",
)

print(f"✅ Webhook configurado: {updated.get('sms_url')}")
print(f"\n🧪 Verifica con:")
print(f"   curl {WEBHOOK_URL}")
print(f"   → debe responder: Webhook activo - Alta Visión / Clarivista")
