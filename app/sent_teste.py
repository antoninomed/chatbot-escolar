import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("META_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v20.0")

TO = input("Digite seu número no formato 55DDDNÚMERO (sem +): ").strip()

url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_NUMBER_ID}/messages"
payload = {
    "messaging_product": "whatsapp",
    "to": TO,
    "type": "text",
    "text": {"body": "Teste direto via Cloud API ✅"},
}
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

resp = httpx.post(url, json=payload, headers=headers, timeout=15.0)
print("status:", resp.status_code)
print("body:", resp.text)