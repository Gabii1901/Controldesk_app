"""Add nome_colaborador to despesas

Revision ID: 1640ad8b9cef
Revises: 
Create Date: 2025-07-05 00:35:46.710736
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1640ad8b9cef'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # ✅ Adiciona somente as colunas necessárias na tabela despesas
    with op.batch_alter_table('despesas', schema=None) as batch_op:
        batch_op.add_column(sa.Column('nome_colaborador', sa.String(length=100), nullable=False))
        batch_op.add_column(sa.Column('cnpj_cpf_local', sa.String(length=18), nullable=False))

def downgrade():
    with op.batch_alter_table('despesas', schema=None) as batch_op:
        batch_op.drop_column('cnpj_cpf_local')
        batch_op.drop_column('nome_colaborador')
