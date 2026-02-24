from fastapi import FastAPI, Request, Response, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.webhooks.messages import handle_messages
from app.meta.signature import verify_meta_signature  # mantenha sua função

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/webhook")
def webhook_verify(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WEBHOOK_VERIFY_TOKEN:
        return Response(content=hub_challenge or "", media_type="text/plain")
    raise HTTPException(status_code=403, detail="Webhook verification failed")

@app.post("/webhook")
async def webhook_receive(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
):
    raw = await request.body()
    if not verify_meta_signature(settings.META_APP_SECRET, raw, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # sempre retornar 200 rápido (produção-safe)
    try:
        db_gen = get_db()
        db: Session = next(db_gen)
        await handle_messages(request, db)
    except Exception as e:
        print("[WEBHOOK] handler error:", repr(e))
    finally:
        try:
            db.close()
        except Exception:
            pass

    return Response(status_code=200)