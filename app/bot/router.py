from sqlalchemy.orm import Session
from app.meta.whatsapp_api import send_text_message

async def handle_incoming(db: Session, tenant_id, from_phone: str, text: str) -> None:
    # MVP: resposta fixa (depois vira fluxo)
    fallback = (
        "Consigo ajudar com: (1) matrícula, (2) documentos, (3) horário da secretaria, "
        "(4) calendário, (5) falar com a secretaria.\n"
        "Qual opção você prefere?"
    )
    await send_text_message(from_phone, fallback)