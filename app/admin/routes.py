from datetime import timezone, datetime
import mimetypes

from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_

from app.db.session import get_db
from app.db.models import UsuarioAdmin, MensagemWhatsapp, Aluno, Tenant, Conversation
from app.admin.auth import verificar_senha, criar_token_sessao, obter_usuario_logado
from app.meta.whatsapp_api import (
    send_text_message,
    upload_media_bytes,
    send_document_message,
    send_image_message,
    send_audio_message,
    send_video_message,
    tipo_conteudo_por_mime,
    baixar_media_meta_para_local,
)
from app.services.mensagens import salvar_mensagem

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


def _usuario_atual(request: Request, db: Session):
    sessao = obter_usuario_logado(request)
    return db.query(UsuarioAdmin).filter(UsuarioAdmin.id == sessao["usuario_id"]).first()


def _query_conversas(usuario, db: Session, busca: str = ""):
    prioridade_status = case(
        (
            and_(
                Conversation.atendimento_humano == True,
                Conversation.status_atendimento == "aguardando"
            ),
            0
        ),
        (
            and_(
                Conversation.atendimento_humano == True,
                Conversation.status_atendimento == "em_atendimento"
            ),
            1
        ),
        (
            Conversation.status_atendimento == "finalizado",
            2
        ),
        else_=3
    )

    query = db.query(
        MensagemWhatsapp.telefone_usuario.label("telefone_usuario"),
        func.max(MensagemWhatsapp.criada_em).label("ultima_data"),
        Conversation.status_atendimento.label("status_atendimento"),
        Conversation.atendimento_humano.label("atendimento_humano"),
        prioridade_status.label("prioridade"),
    ).outerjoin(
        Conversation,
        and_(
            Conversation.tenant_id == usuario.id_escola,
            Conversation.user_wa_id == MensagemWhatsapp.telefone_usuario
        )
    ).filter(
        MensagemWhatsapp.id_escola == usuario.id_escola
    )

    if busca:
        query = query.filter(MensagemWhatsapp.telefone_usuario.ilike(f"%{busca}%"))

    conversas = query.group_by(
        MensagemWhatsapp.telefone_usuario,
        Conversation.status_atendimento,
        Conversation.atendimento_humano,
    ).order_by(
        prioridade_status.asc(),
        func.max(MensagemWhatsapp.criada_em).desc()
    ).all()

    return conversas


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "erro": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db),
):
    usuario = db.query(UsuarioAdmin).filter(
        UsuarioAdmin.email == email,
        UsuarioAdmin.ativo == True
    ).first()

    if not usuario or not verificar_senha(senha, usuario.senha_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "erro": "E-mail ou senha inválidos."}
        )

    token = criar_token_sessao(str(usuario.id))
    response = RedirectResponse(url="/admin", status_code=302)
    response.set_cookie("admin_session", token, httponly=True, samesite="lax")
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("admin_session")
    return response


@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    usuario = _usuario_atual(request, db)
    escola = db.query(Tenant).filter(Tenant.id == usuario.id_escola).first()

    atendimentos_pendentes = db.query(Conversation).filter(
    Conversation.tenant_id == usuario.id_escola,
    Conversation.status_atendimento == "aguardando"
    ).count()

    conversas_pendentes = db.query(
    MensagemWhatsapp.telefone_usuario,
    func.max(MensagemWhatsapp.criada_em).label("ultima_data")
    ).join(
        Conversation,
        and_(
            Conversation.user_wa_id == MensagemWhatsapp.telefone_usuario,
            Conversation.tenant_id == usuario.id_escola
        )
    ).filter(
        Conversation.status_atendimento == "aguardando",
        MensagemWhatsapp.id_escola == usuario.id_escola
    ).group_by(
        MensagemWhatsapp.telefone_usuario
    ).order_by(
        func.max(MensagemWhatsapp.criada_em).desc()
    ).limit(6).all()






    total_mensagens = db.query(MensagemWhatsapp).filter(
        MensagemWhatsapp.id_escola == usuario.id_escola
    ).count()

    total_recebidas = db.query(MensagemWhatsapp).filter(
        MensagemWhatsapp.id_escola == usuario.id_escola,
        MensagemWhatsapp.tipo_mensagem == "recebida"
    ).count()

    total_enviadas = db.query(MensagemWhatsapp).filter(
        MensagemWhatsapp.id_escola == usuario.id_escola,
        MensagemWhatsapp.tipo_mensagem == "enviada"
    ).count()

    total_alunos = db.query(Aluno).filter(
        Aluno.id_escola == usuario.id_escola,
        Aluno.ativo == True
    ).count()

    ultimas_mensagens = db.query(MensagemWhatsapp).filter(
        MensagemWhatsapp.id_escola == usuario.id_escola
    ).order_by(MensagemWhatsapp.criada_em.desc()).limit(10).all()

    conversas_ativas = db.query(
        MensagemWhatsapp.telefone_usuario,
        func.max(MensagemWhatsapp.criada_em).label("ultima_data")
    ).filter(
        MensagemWhatsapp.id_escola == usuario.id_escola
    ).group_by(
        MensagemWhatsapp.telefone_usuario
    ).order_by(
        func.max(MensagemWhatsapp.criada_em).desc()
    ).limit(8).all()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "usuario": usuario,
            "escola": escola,
            "total_mensagens": total_mensagens,
            "total_recebidas": total_recebidas,
            "total_enviadas": total_enviadas,
            "total_alunos": total_alunos,
            "ultimas_mensagens": ultimas_mensagens,
            "conversas_ativas": conversas_ativas,
            "atendimentos_pendentes": atendimentos_pendentes,
            "conversas_pendentes": conversas_pendentes,


        }
    )


@router.get("/conversas", response_class=HTMLResponse)
def listar_conversas(request: Request, busca: str = "", db: Session = Depends(get_db)):
    usuario = _usuario_atual(request, db)
    conversas = _query_conversas(usuario, db, busca)

    return templates.TemplateResponse(
        "conversas.html",
        {
            "request": request,
            "usuario": usuario,
            "conversas": conversas,
            "busca": busca,
        }
    )


@router.get("/conversas/parcial", response_class=HTMLResponse)
def listar_conversas_parcial(request: Request, busca: str = "", db: Session = Depends(get_db)):
    usuario = _usuario_atual(request, db)
    conversas = _query_conversas(usuario, db, busca)

    return templates.TemplateResponse(
        "partials/conversas_lista.html",
        {
            "request": request,
            "usuario": usuario,
            "conversas": conversas,
            "busca": busca,
        }
    )


@router.get("/conversas/{telefone}/mensagens", response_class=HTMLResponse)
def detalhe_conversa_mensagens(telefone: str, request: Request, db: Session = Depends(get_db)):
    usuario = _usuario_atual(request, db)

    mensagens = db.query(MensagemWhatsapp).filter(
        MensagemWhatsapp.id_escola == usuario.id_escola,
        MensagemWhatsapp.telefone_usuario == telefone
    ).order_by(MensagemWhatsapp.criada_em.asc()).all()

    conversa = db.query(Conversation).filter(
        Conversation.tenant_id == usuario.id_escola,
        Conversation.user_wa_id == telefone
    ).first()

    return templates.TemplateResponse(
        "partials/conversa_mensagens.html",
        {
            "request": request,
            "usuario": usuario,
            "telefone": telefone,
            "mensagens": mensagens,
            "conversa": conversa,
        }
    )


@router.get("/conversas/{telefone}", response_class=HTMLResponse)
def detalhe_conversa(telefone: str, request: Request, db: Session = Depends(get_db)):
    usuario = _usuario_atual(request, db)

    mensagens = db.query(MensagemWhatsapp).filter(
        MensagemWhatsapp.id_escola == usuario.id_escola,
        MensagemWhatsapp.telefone_usuario == telefone
    ).order_by(MensagemWhatsapp.criada_em.asc()).all()

    conversa = db.query(Conversation).filter(
        Conversation.tenant_id == usuario.id_escola,
        Conversation.user_wa_id == telefone
    ).first()

    return templates.TemplateResponse(
        "conversa_detalhe.html",
        {
            "request": request,
            "usuario": usuario,
            "telefone": telefone,
            "mensagens": mensagens,
            "conversa": conversa,
        }
    )


@router.post("/conversas/{telefone}/responder")
async def responder_conversa(
    telefone: str,
    request: Request,
    mensagem: str = Form(""),
    acao: str = Form(""),
    arquivos: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    usuario = _usuario_atual(request, db)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if not usuario:
        if is_ajax:
            return JSONResponse(
                {"ok": False, "error": "Sessão expirada. Faça login novamente."},
                status_code=401
            )
        return RedirectResponse(url="/admin/login", status_code=302)

    conversa = db.query(Conversation).filter(
        Conversation.tenant_id == usuario.id_escola,
        Conversation.user_wa_id == telefone
    ).first()

    if not conversa:
        if is_ajax:
            return JSONResponse(
                {"ok": False, "error": "Conversa não encontrada."},
                status_code=404
            )
        return RedirectResponse(url="/admin/conversas", status_code=302)

    mensagem = (mensagem or "").strip()
    acao = (acao or "").strip()
    arquivos_validos = [arquivo for arquivo in arquivos if arquivo and arquivo.filename]

    try:
        if acao == "finalizar":
            mensagem_finalizacao = (
                "Obrigado pelo contato! 😊\n\n"
                "Seu atendimento foi encerrado e esperamos ter ajudado da melhor forma possível.\n\n"
                "Sempre que precisar, estaremos à disposição."
            )

            await send_text_message(telefone, mensagem_finalizacao)

            salvar_mensagem(
                db=db,
                id_escola=usuario.id_escola,
                telefone_usuario=telefone,
                tipo_mensagem="enviada",
                conteudo=mensagem_finalizacao,
                tipo_conteudo="texto",
            )

            conversa.atendimento_humano = False
            conversa.status_atendimento = "finalizado"
            conversa.state = "inicio"
            conversa.last_message_at = datetime.now(timezone.utc)
            db.commit()

            if is_ajax:
                return JSONResponse({
                    "ok": True,
                    "finalizado": True,
                    "redirect_url": "/admin/conversas"
                })

            return RedirectResponse(url="/admin/conversas", status_code=302)

        tem_arquivo = len(arquivos_validos) > 0

        if not mensagem and not tem_arquivo:
            if is_ajax:
                return JSONResponse(
                    {"ok": False, "error": "Digite uma mensagem ou anexe um arquivo."},
                    status_code=400
                )
            return RedirectResponse(url=f"/admin/conversas/{telefone}", status_code=302)

        if tem_arquivo:
            from app.meta.whatsapp_api import _local_media_path

            total_arquivos = len(arquivos_validos)

            for i, arquivo in enumerate(arquivos_validos):
                file_bytes = await arquivo.read()
                mime_type = (
                    arquivo.content_type
                    or mimetypes.guess_type(arquivo.filename)[0]
                    or "application/octet-stream"
                )
                media_id = await upload_media_bytes(file_bytes, arquivo.filename, mime_type)
                tipo_conteudo = tipo_conteudo_por_mime(mime_type)

                caption_atual = mensagem if (mensagem and i == total_arquivos - 1) else None

                if tipo_conteudo == "imagem":
                    await send_image_message(telefone, media_id, caption=caption_atual)
                elif tipo_conteudo == "audio":
                    await send_audio_message(telefone, media_id)
                    if caption_atual:
                        await send_text_message(telefone, caption_atual)
                elif tipo_conteudo == "video":
                    await send_video_message(telefone, media_id, caption=caption_atual)
                else:
                    await send_document_message(
                        telefone,
                        media_id,
                        arquivo.filename,
                        caption=caption_atual
                    )

                local_path, public_url = _local_media_path(arquivo.filename, mime_type)

                with open(local_path, "wb") as f:
                    f.write(file_bytes)

                salvar_mensagem(
                    db=db,
                    id_escola=usuario.id_escola,
                    telefone_usuario=telefone,
                    tipo_mensagem="enviada",
                    conteudo=caption_atual if caption_atual else "",
                    tipo_conteudo=tipo_conteudo,
                    media_url=public_url,
                    media_mime_type=mime_type,
                    media_filename=arquivo.filename,
                    media_id=media_id,
                )

        elif mensagem:
            await send_text_message(telefone, mensagem)
            salvar_mensagem(
                db=db,
                id_escola=usuario.id_escola,
                telefone_usuario=telefone,
                tipo_mensagem="enviada",
                conteudo=mensagem,
                tipo_conteudo="texto",
            )

        conversa.atendimento_humano = True
        conversa.status_atendimento = "em_atendimento"
        conversa.last_message_at = datetime.now(timezone.utc)
        db.commit()

        if is_ajax:
            return JSONResponse({"ok": True})

        return RedirectResponse(url=f"/admin/conversas/{telefone}", status_code=302)

    except Exception as e:
        db.rollback()

        if is_ajax:
            return JSONResponse(
                {"ok": False, "error": f"Erro ao enviar mensagem: {str(e)}"},
                status_code=500
            )

        raise e


@router.get("/alunos", response_class=HTMLResponse)
def listar_alunos(request: Request, busca: str = "", db: Session = Depends(get_db)):
    usuario = _usuario_atual(request, db)

    query = db.query(Aluno).filter(
        Aluno.id_escola == usuario.id_escola,
        Aluno.ativo == True
    )

    if busca:
        query = query.filter(Aluno.nome_aluno.ilike(f"%{busca}%"))

    alunos = query.order_by(Aluno.nome_aluno.asc()).all()

    return templates.TemplateResponse(
        "alunos.html",
        {
            "request": request,
            "usuario": usuario,
            "alunos": alunos,
            "busca": busca,
        }
    )


@router.get("/alunos/{aluno_id}/editar", response_class=HTMLResponse)
def editar_aluno_page(aluno_id: str, request: Request, db: Session = Depends(get_db)):
    usuario = _usuario_atual(request, db)

    aluno = db.query(Aluno).filter(
        Aluno.id == aluno_id,
        Aluno.id_escola == usuario.id_escola
    ).first()

    return templates.TemplateResponse(
        "aluno_editar.html",
        {
            "request": request,
            "usuario": usuario,
            "aluno": aluno,
        }
    )


@router.post("/alunos/{aluno_id}/editar")
def editar_aluno_submit(
    aluno_id: str,
    request: Request,
    status_matricula: str = Form(""),
    status_rematricula: str = Form(""),
    status_financeiro: str = Form(""),
    horario_saida: str = Form(""),
    serie: str = Form(""),
    turno: str = Form(""),
    db: Session = Depends(get_db),
):
    usuario = _usuario_atual(request, db)

    aluno = db.query(Aluno).filter(
        Aluno.id == aluno_id,
        Aluno.id_escola == usuario.id_escola
    ).first()

    aluno.status_matricula = status_matricula
    aluno.status_rematricula = status_rematricula
    aluno.status_financeiro = status_financeiro
    aluno.horario_saida = horario_saida
    aluno.serie = serie
    aluno.turno = turno
    db.commit()

    return RedirectResponse(url="/admin/alunos", status_code=302)


@router.get("/faq", response_class=HTMLResponse)
def faq_page(request: Request, db: Session = Depends(get_db)):
    usuario = _usuario_atual(request, db)
    return templates.TemplateResponse(
        "faq.html",
        {"request": request, "usuario": usuario}
    )


@router.get("/configuracoes", response_class=HTMLResponse)
def configuracoes_page(request: Request, db: Session = Depends(get_db)):
    usuario = _usuario_atual(request, db)
    escola = db.query(Tenant).filter(Tenant.id == usuario.id_escola).first()

    return templates.TemplateResponse(
        "configuracoes.html",
        {"request": request, "usuario": usuario, "escola": escola}
    )
