"""Add field admindiv.gaul

Revision ID: 50e54a034fa5
Revises: cdcea4ae97ed
Create Date: 2025-12-19 12:21:52.532645

"""

# revision identifiers, used by Alembic.
revision = '50e54a034fa5'
down_revision = 'cdcea4ae97ed'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    op.add_column(
        'administrativedivision',
        sa.Column('gaul', sa.Integer(), nullable=True),
        schema='datamart',
    )
    op.create_index(
        op.f('ix_datamart_administrativedivision_gaul'),
        'administrativedivision',
        ['gaul'],
        # unique=True,
        schema='datamart',
    )

def downgrade(engine_name):
    op.drop_index(
        op.f('ix_datamart_administrativedivision_gaul'),
        table_name='administrativedivision',
        schema='datamart',
    )
    op.drop_column('administrativedivision', 'gaul', schema='datamart')
