# app/bot/flows.py
from __future__ import annotations
from app.bot.menus import main_menu_buttons

def enrollment_flow():
    return (
        "Para matrícula, envie:\n"
        "• Nome do aluno\n"
        "• Série/ano\n"
        "• Turno (manhã ou tarde)\n\n"
        "Encaminharei para a secretaria."
    )

def docs_flow():
    return (
        "Os documentos básicos são:\n"
        "• RG e CPF do responsável\n"
        "• Certidão do aluno\n"
        "• Comprovante de residência\n"
        "• Histórico escolar"
    )