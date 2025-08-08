"""Remove colaborador_id from despesas

Revision ID: fbc4563251fb
Revises: 1640ad8b9cef
Create Date: 2025-07-05 00:45:11.266918

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fbc4563251fb'
down_revision = '1640ad8b9cef'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('despesas', schema=None) as batch_op:
        # Remover a FK e a coluna colaborador_id
        batch_op.drop_constraint(batch_op.f('despesas_colaborador_id_fkey'), type_='foreignkey')
        batch_op.drop_column('colaborador_id')

def downgrade():
    with op.batch_alter_table('despesas', schema=None) as batch_op:
        # Recriar a coluna colaborador_id e a FK, caso faça downgrade
        batch_op.add_column(sa.Column('colaborador_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key(
            batch_op.f('despesas_colaborador_id_fkey'),
            'colaboradores',
            ['colaborador_id'], ['id'],
            ondelete='CASCADE'
        )
