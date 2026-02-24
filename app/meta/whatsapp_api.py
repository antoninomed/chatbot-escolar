import httpx
from app.config import settings

async def send_text_message(to_phone: str, body: str) -> bool:
    url = f"https://graph.facebook.com/{settings.META_GRAPH_VERSION}/{settings.META_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": body},
    }
    headers = {
        "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code >= 400:
        print("[META] send failed:", resp.status_code, resp.text)
        return False

    print("[META] send ok:", resp.text)
    return True