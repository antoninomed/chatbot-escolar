from fastapi import Request
from sqlalchemy.orm import Session
from app.tenants.resolver import resolve_tenant_by_phone_number_id
from app.db.models import ProcessedMessage
from app.bot.router import handle_incoming

async def handle_messages(request: Request, db: Session) -> None:
    body = await request.json()

    entry = (body.get("entry") or [{}])[0]
    changes = (entry.get("changes") or [{}])[0]
    value = changes.get("value") or {}

    # Status events (delivered/failed/read)
    statuses = value.get("statuses") or []
    if statuses:
        print("[STATUSES]", statuses)
        return

    # Mensagens recebidas
    messages = value.get("messages") or []
    metadata = value.get("metadata") or {}
    phone_number_id = metadata.get("phone_number_id")

    if not phone_number_id:
        print("[WEBHOOK] missing metadata.phone_number_id")
        return

    tenant = resolve_tenant_by_phone_number_id(db, str(phone_number_id))
    if not tenant:
        print("[WEBHOOK] tenant not found for phone_number_id:", phone_number_id)
        return

    if not messages:
        return

    msg = messages[0]
    msg_id = msg.get("id")
    from_phone = msg.get("from")
    msg_type = msg.get("type")
    text = ((msg.get("text") or {}).get("body") or "").strip()

    # Idempotência
    if msg_id:
        exists = db.query(ProcessedMessage).filter(
            ProcessedMessage.tenant_id == tenant.id,
            ProcessedMessage.message_id == msg_id
        ).first()
        if exists:
            print("[IDEMPOTENCY] already processed:", msg_id)
            return

        db.add(ProcessedMessage(tenant_id=tenant.id, message_id=msg_id))
        db.commit()

    print("[INBOUND]", {"tenant": tenant.name, "from": from_phone, "type": msg_type, "text": text})



    if msg_type != "text" or not from_phone or not text:
        return

    await handle_incoming(db=db, tenant_id=tenant.id, from_phone=from_phone, text=text)