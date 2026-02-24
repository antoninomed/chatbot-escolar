import os
import httpx
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("META_ACCESS_TOKEN")
phone_id = os.getenv("META_PHONE_NUMBER_ID")
version = os.getenv("META_GRAPH_VERSION", "v20.0")

url = f"https://graph.facebook.com/{version}/{phone_id}"
params = {"fields": "display_phone_number,verified_name"}

headers = {"Authorization": f"Bearer {token}"}

r = httpx.get(url, params=params, headers=headers, timeout=15.0)
print("status:", r.status_code)
print("body:", r.text)