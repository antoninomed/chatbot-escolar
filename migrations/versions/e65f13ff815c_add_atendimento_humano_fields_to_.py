"""add atendimento humano fields to conversations

Revision ID: e65f13ff815c
Revises: 55cfffa87a34
Create Date: 2026-03-11 23:47:59.185644

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e65f13ff815c'
down_revision: Union[str, Sequence[str], None] = '55cfffa87a34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "conversations",
        sa.Column("atendimento_humano", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "conversations",
        sa.Column("status_atendimento", sa.String(), nullable=True)
    )
    op.add_column(
        "conversations",
        sa.Column("assunto", sa.String(), nullable=True)
    )


def downgrade():
    op.drop_column("conversations", "assunto")
    op.drop_column("conversations", "status_atendimento")
    op.drop_column("conversations", "atendimento_humano")