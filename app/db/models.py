import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)
    whatsapp_phone_number_id = Column(String(64), unique=True, nullable=False)
    timezone = Column(String(32), nullable=False, default="America/Fortaleza")
    config_json = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ProcessedMessage(Base):
    __tablename__ = "processed_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    message_id = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "message_id", name="uq_processed_tenant_msg"),
    )


class FAQ(Base):
    __tablename__ = "faq"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Aluno(Base):
    __tablename__ = "alunos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_escola = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    nome_aluno = Column(String(150), nullable=False)
    nome_responsavel = Column(String(150), nullable=True)
    codigo_matricula = Column(String(50), nullable=True)
    serie = Column(String(50), nullable=True)
    turno = Column(String(50), nullable=True)
    status_matricula = Column(String(50), nullable=True)
    status_rematricula = Column(String(50), nullable=True)
    status_financeiro = Column(String(50), nullable=True)
    horario_saida = Column(String(20), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    escola = relationship("Tenant")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_wa_id = Column(String(32), nullable=False)
    state = Column(String(64), nullable=False, default="inicio")
    contexto_json = Column(JSONB, nullable=False, default=dict)
    last_message_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    atendimento_humano = Column(Boolean, default=False)
    status_atendimento = Column(String, nullable=True)
    assunto = Column(String, nullable=True)


class MensagemWhatsapp(Base):
    __tablename__ = "mensagens_whatsapp"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_escola = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    telefone_usuario = Column(String(30), nullable=False)
    tipo_mensagem = Column(String(20), nullable=False)  # recebida / enviada
    conteudo = Column(Text, nullable=True)
    mensagem_id_whatsapp = Column(String(120), nullable=True)

    # Novos campos para mídia
    tipo_conteudo = Column(String(30), nullable=False, default="texto")  # texto, imagem, pdf, audio, video, documento, arquivo
    media_url = Column(Text, nullable=True)
    media_mime_type = Column(String(255), nullable=True)
    media_filename = Column(String(255), nullable=True)
    media_id = Column(String(255), nullable=True)

    criada_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UsuarioAdmin(Base):
    __tablename__ = "usuarios_admin"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_escola = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)

    nome = Column(String(120), nullable=False)
    email = Column(String(120), nullable=False, unique=True)
    senha_hash = Column(String(255), nullable=False)

    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "telefone", name="uq_contact_tenant_telefone"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    nome = Column(String(150), nullable=False)
    telefone = Column(String(30), nullable=False, index=True)
    email = Column(String(150), nullable=True)
    observacoes = Column(String(255), nullable=True)