# app/bot/menus.py
from __future__ import annotations

def main_menu_list(school_name: str) -> tuple[str, str, list[dict]]:
    body = (
        f"Olá! 👋\n"
        f"Sou o atendimento automático da *{school_name}*.\n\n"
        f"Selecione uma opção:"
    )

    button_text = "Abrir menu"

    sections = [
        {
            "title": "Atendimento",
            "rows": [
                {"id": "ENROLL", "title": "📘 Matrícula", "description": "Matrícula e rematrícula"},
                {"id": "DOCS", "title": "📄 Documentos", "description": "Lista e orientações"},
                {"id": "HOURS", "title": "🕘 Horário", "description": "Atendimento da secretaria"},
                {"id": "CALENDAR", "title": "🗓️ Calendário", "description": "Provas, reuniões e feriados"},
            ],
        },
        {
            "title": "Informações",
            "rows": [
                {"id": "FINANCE", "title": "💳 Pagamentos", "description": "Mensalidade e financeiro"},
                {"id": "LOCATION", "title": "📍 Endereço", "description": "Localização e referência"},
                {"id": "SECRETARY", "title": "👩‍💼 Secretaria", "description": "Falar com atendimento humano"},
            ],
        },
        {
            "title": "Dúvidas",
            "rows": [
                {"id": "FAQ", "title": "❓ Dúvidas", "description": "Uniforme, material, transferência..."},
            ],
        },
    ]

    return body, button_text, sections