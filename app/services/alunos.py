from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import Aluno


def buscar_aluno_por_nome(db: Session, id_escola, nome_aluno: str):
    nome_normalizado = nome_aluno.strip().lower()

    return db.query(Aluno).filter(
        Aluno.id_escola == id_escola,
        Aluno.ativo == True,
        func.lower(Aluno.nome_aluno) == nome_normalizado
    ).first()


def buscar_aluno_por_nome_parcial(db: Session, id_escola, nome_aluno: str):
    return db.query(Aluno).filter(
        Aluno.id_escola == id_escola,
        Aluno.ativo == True,
        Aluno.nome_aluno.ilike(f"%{nome_aluno.strip()}%")
    ).limit(5).all()


def obter_status_rematricula(db: Session, id_escola, nome_aluno: str):
    aluno = buscar_aluno_por_nome(db, id_escola, nome_aluno)
    if not aluno:
        return None
    return aluno.status_rematricula, aluno


def obter_status_matricula(db: Session, id_escola, nome_aluno: str):
    aluno = buscar_aluno_por_nome(db, id_escola, nome_aluno)
    if not aluno:
        return None
    return aluno.status_matricula, aluno


def obter_status_financeiro(db: Session, id_escola, nome_aluno: str):
    aluno = buscar_aluno_por_nome(db, id_escola, nome_aluno)
    if not aluno:
        return None
    return aluno.status_financeiro, aluno


def obter_horario_saida(db: Session, id_escola, nome_aluno: str):
    aluno = buscar_aluno_por_nome(db, id_escola, nome_aluno)
    if not aluno:
        return None
    return aluno.horario_saida, aluno
