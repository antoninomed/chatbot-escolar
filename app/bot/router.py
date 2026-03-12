from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from app.config import settings
from app.meta.whatsapp_api import baixar_media_meta_para_local, send_list_message, send_text_message, tipo_conteudo_por_mime
from app.bot.menus import main_menu_list
from app.bot.faq_router import resolve_faq

from app.services.mensagens import salvar_mensagem
from app.meta.whatsapp_api import baixar_media_meta_para_local, tipo_conteudo_por_mime


from app.services.conversas import (
    obter_ou_criar_conversa,
    atualizar_estado_conversa,
    resetar_conversa,
    tratar_estado_ao_receber_mensagem,
)
from app.services.alunos import (
    obter_status_matricula,
    obter_status_rematricula,
    obter_status_financeiro,
    obter_horario_saida,
)

# tempo máximo com atendimento humano aberto sem interação válida
ATENDIMENTO_HUMANO_TIMEOUT_HORAS = 12


def _agora_utc():
    return datetime.now(timezone.utc)


def _expirou_atendimento_humano(conversa) -> bool:
    if not getattr(conversa, "atendimento_humano", False):
        return False

    last_message_at = getattr(conversa, "last_message_at", None)
    if not last_message_at:
        return False

    # garante timezone-aware
    if last_message_at.tzinfo is None:
        last_message_at = last_message_at.replace(tzinfo=timezone.utc)

    limite = _agora_utc() - timedelta(hours=ATENDIMENTO_HUMANO_TIMEOUT_HORAS)
    return last_message_at < limite


def _encerrar_atendimento_humano(db: Session, conversa, status_final: str | None = None):
    conversa.atendimento_humano = False
    conversa.status_atendimento = status_final
    resetar_conversa(db, conversa)
    conversa.last_message_at = _agora_utc()
    db.commit()


def _atualizar_ultima_interacao(db: Session, conversa):
    conversa.last_message_at = _agora_utc()
    db.commit()


async def processar_mensagem_recebida(payload_mensagem, db, id_escola):
    telefone = payload_mensagem["from"]
    tipo = payload_mensagem.get("type")

    if tipo == "text":
        texto = payload_mensagem["text"]["body"]

        salvar_mensagem(
            db=db,
            id_escola=id_escola,
            telefone_usuario=telefone,
            tipo_mensagem="recebida",
            conteudo=texto,
            tipo_conteudo="texto",
        )
        return

    if tipo in ["image", "document", "audio", "video"]:
        bloco = payload_mensagem.get(tipo, {})
        media_id = bloco.get("id")
        mime_type = bloco.get("mime_type")
        filename = bloco.get("filename")
        caption = bloco.get("caption", "")

        media_info = await baixar_media_meta_para_local(
            media_id=media_id,
            filename=filename,
            mime_type=mime_type,
        )

        salvar_mensagem(
            db=db,
            id_escola=id_escola,
            telefone_usuario=telefone,
            tipo_mensagem="recebida",
            conteudo=caption,
            tipo_conteudo=tipo_conteudo_por_mime(media_info.get("media_mime_type")),
            media_url=media_info.get("media_url"),
            media_mime_type=media_info.get("media_mime_type"),
            media_filename=media_info.get("media_filename"),
            media_id=media_info.get("media_id"),
        )
        return




async def _enviar_texto_e_salvar(
    db: Session,
    tenant_id,
    from_phone: str,
    mensagem: str,
):
    await send_text_message(from_phone, mensagem)

    salvar_mensagem(
        db=db,
        id_escola=tenant_id,
        telefone_usuario=from_phone,
        tipo_mensagem="enviada",
        conteudo=mensagem,
    )


async def _enviar_menu_principal(
    db: Session,
    tenant_id,
    from_phone: str,
    school_name: str,
):
    body, button_text, sections = main_menu_list(school_name)

    await send_list_message(from_phone, body, button_text, sections)

    salvar_mensagem(
        db=db,
        id_escola=tenant_id,
        telefone_usuario=from_phone,
        tipo_mensagem="enviada",
        conteudo=f"[menu_lista] {body}",
    )


async def handle_incoming(
    db: Session,
    tenant_id,
    from_phone: str,
    text: str,
    button_id: str | None = None
) -> None:
    school_name = getattr(settings, "SCHOOL_NAME", "Escola")
    texto = (text or "").strip()

    conversa = obter_ou_criar_conversa(db, tenant_id, from_phone)

    conversa = tratar_estado_ao_receber_mensagem(db, conversa)
    # -------------------------------------------------
    # 1) EXPIRAÇÃO AUTOMÁTICA DO ATENDIMENTO HUMANO
    # -------------------------------------------------
    if _expirou_atendimento_humano(conversa):
        _encerrar_atendimento_humano(db, conversa, "expirado")

    # -------------------------------------------------
    # 2) CLIQUE EM BOTÃO SEMPRE DEVOLVE PARA O BOT
    # -------------------------------------------------
    # Se o usuário clicou em qualquer item do menu, entendemos que ele quer
    # sair do atendimento humano e voltar ao fluxo automático.
    if button_id and getattr(conversa, "atendimento_humano", False):
        _encerrar_atendimento_humano(db, conversa, None)
        conversa = obter_ou_criar_conversa(db, tenant_id, from_phone)

    # -------------------------------------------------
    # 3) COMANDO UNIVERSAL PARA VOLTAR AO MENU
    # -------------------------------------------------
    if texto.lower() in ["menu", "inicio", "início", "voltar"]:
        _encerrar_atendimento_humano(db, conversa, None)
        await _enviar_menu_principal(db, tenant_id, from_phone, school_name)
        return

    # -------------------------------------------------
    # 4) ATUALIZA TIMESTAMP DE ÚLTIMA INTERAÇÃO
    # -------------------------------------------------
    _atualizar_ultima_interacao(db, conversa)

    # -----------------------------------
    # 5) CLIQUE EM ITEM DA LISTA / BOTÃO
    # -----------------------------------
    if button_id:
        if button_id == "ENROLL":
            atualizar_estado_conversa(db, conversa, "aguardando_nome_matricula")
            _atualizar_ultima_interacao(db, conversa)
            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "✅ Matrícula: informe o nome completo do aluno para consultar a situação da matrícula."
            )
            return

        if button_id == "REENROLL":
            atualizar_estado_conversa(db, conversa, "aguardando_nome_rematricula")
            _atualizar_ultima_interacao(db, conversa)
            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "🔄 Rematrícula: informe o nome completo do aluno para consultar a situação da rematrícula."
            )
            return

        if button_id == "FINANCE":
            atualizar_estado_conversa(db, conversa, "aguardando_nome_financeiro")
            _atualizar_ultima_interacao(db, conversa)
            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "💳 Situação financeira: informe o nome completo do aluno."
            )
            return

        if button_id == "DISMISSAL":
            atualizar_estado_conversa(db, conversa, "aguardando_nome_saida")
            _atualizar_ultima_interacao(db, conversa)
            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "🕒 Horário de saída: informe o nome completo do aluno."
            )
            return

        if button_id == "DOCS":
            resetar_conversa(db, conversa)
            _atualizar_ultima_interacao(db, conversa)
            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "📄 Documentos: RG/CPF do responsável, certidão do aluno, comprovante de residência e histórico escolar."
            )
            return

        if button_id == "HOURS":
            resetar_conversa(db, conversa)
            _atualizar_ultima_interacao(db, conversa)
            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "🕘 Secretaria: seg–sex 08:00–17:00."
            )
            return

        if button_id == "CALENDAR":
            resetar_conversa(db, conversa)
            _atualizar_ultima_interacao(db, conversa)
            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "🗓️ Calendário: diga série/ano e o que deseja consultar (provas, reuniões, feriados)."
            )
            return

        if button_id == "LOCATION":
            resetar_conversa(db, conversa)
            _atualizar_ultima_interacao(db, conversa)
            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "📍 Endereço: (coloque aqui o endereço). Se disser seu bairro, envio referência."
            )
            return

        if button_id == "SECRETARY":
            conversa.atendimento_humano = True
            conversa.status_atendimento = "aguardando"
            atualizar_estado_conversa(db, conversa, "aguardando_secretaria")
            conversa.last_message_at = _agora_utc()
            db.commit()

            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "Seu atendimento foi encaminhado para a secretaria. Por favor, envie agora:\n\n1. Seu nome\n2. Nome do aluno\n3. Assunto\n\nNossa equipe responderá por aqui."
            )
            return

        if button_id == "FAQ":
            resetar_conversa(db, conversa)
            _atualizar_ultima_interacao(db, conversa)
            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "❓ Pergunte sobre: uniforme, material, transferência, turno, integral, avaliações, alimentação, transporte."
            )
            return

    # -------------------------------------------------
    # 6) BLOQUEIO DE ATENDIMENTO HUMANO
    # -------------------------------------------------
    # Enquanto estiver ativo, o bot não responde automaticamente.
    # Exceção: quando ainda estamos esperando a primeira mensagem do usuário
    # para a secretaria.
    if getattr(conversa, "atendimento_humano", False):
        if conversa.state == "aguardando_secretaria":
            pass
        else:
            conversa.status_atendimento = "aguardando"
            conversa.last_message_at = _agora_utc()
            db.commit()
            return

    # -----------------------------------
    # 7) FLUXOS BASEADOS EM ESTADO
    # -----------------------------------

    if conversa.state == "aguardando_nome_matricula":
        resultado = obter_status_matricula(db, tenant_id, texto)

        if not resultado:
            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "Não encontrei esse aluno. Confira o nome completo e tente novamente, ou digite MENU para voltar."
            )
            return

        status, aluno = resultado
        status_formatado = status or "não informado"

        if str(status_formatado).strip().lower() == "ok":
            mensagem = f"✅ A matrícula de {aluno.nome_aluno} está OK."
        else:
            mensagem = f"ℹ️ A matrícula de {aluno.nome_aluno} está {status_formatado}."

        resetar_conversa(db, conversa)
        _atualizar_ultima_interacao(db, conversa)
        await _enviar_texto_e_salvar(db, tenant_id, from_phone, mensagem)
        return

    if conversa.state == "aguardando_nome_rematricula":
        resultado = obter_status_rematricula(db, tenant_id, texto)

        if not resultado:
            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "Não encontrei esse aluno. Confira o nome completo e tente novamente, ou digite MENU para voltar."
            )
            return

        status, aluno = resultado
        status_formatado = status or "não informado"

        if str(status_formatado).strip().lower() == "ok":
            mensagem = f"✅ A rematrícula de {aluno.nome_aluno} está OK."
        else:
            mensagem = f"ℹ️ A rematrícula de {aluno.nome_aluno} está {status_formatado}."

        resetar_conversa(db, conversa)
        _atualizar_ultima_interacao(db, conversa)
        await _enviar_texto_e_salvar(db, tenant_id, from_phone, mensagem)
        return

    if conversa.state == "aguardando_nome_financeiro":
        resultado = obter_status_financeiro(db, tenant_id, texto)

        if not resultado:
            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "Não encontrei esse aluno. Confira o nome completo e tente novamente, ou digite MENU para voltar."
            )
            return

        status, aluno = resultado
        status_formatado = status or "não informado"

        mensagem = f"💳 A situação financeira de {aluno.nome_aluno} está {status_formatado}."
        resetar_conversa(db, conversa)
        _atualizar_ultima_interacao(db, conversa)
        await _enviar_texto_e_salvar(db, tenant_id, from_phone, mensagem)
        return

    if conversa.state == "aguardando_nome_saida":
        resultado = obter_horario_saida(db, tenant_id, texto)

        if not resultado:
            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "Não encontrei esse aluno. Confira o nome completo e tente novamente, ou digite MENU para voltar."
            )
            return

        horario, aluno = resultado
        horario_formatado = horario or "não informado"

        mensagem = f"🕒 O horário de saída de {aluno.nome_aluno} é {horario_formatado}."
        resetar_conversa(db, conversa)
        _atualizar_ultima_interacao(db, conversa)
        await _enviar_texto_e_salvar(db, tenant_id, from_phone, mensagem)
        return

    if conversa.state == "aguardando_secretaria":
        if not texto:
            await _enviar_texto_e_salvar(
                db,
                tenant_id,
                from_phone,
                "Por favor, envie sua mensagem para que a secretaria possa analisar o atendimento."
            )
            return

        conversa.assunto = texto
        conversa.status_atendimento = "aguardando"
        resetar_conversa(db, conversa)
        conversa.last_message_at = _agora_utc()
        db.commit()

        await _enviar_texto_e_salvar(
            db,
            tenant_id,
            from_phone,
            "Mensagem recebida. A secretaria responderá por aqui assim que possível."
        )
        return

    # -----------------------------------
    # 8) TEXTO LIVRE → TENTA FAQ
    # -----------------------------------
    if texto:
        ans = resolve_faq(texto) if "resolve_faq" in globals() else None
        if ans:
            resetar_conversa(db, conversa)
            _atualizar_ultima_interacao(db, conversa)
            await _enviar_texto_e_salvar(db, tenant_id, from_phone, ans)
            return

    # -----------------------------------
    # 9) FALLBACK → MENU LIST
    # -----------------------------------
    resetar_conversa(db, conversa)
    _atualizar_ultima_interacao(db, conversa)
    await _enviar_menu_principal(db, tenant_id, from_phone, school_name)