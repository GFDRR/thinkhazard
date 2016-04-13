"""Remove column output.coverage

Revision ID: d49029073f8f
Revises: f58bd58cd6d4
Create Date: 2016-04-13 11:10:24.638308

"""

# revision identifiers, used by Alembic.
revision = 'd49029073f8f'
down_revision = 'f58bd58cd6d4'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    op.drop_column('output', 'coverage_ratio', schema='processing')


def downgrade(engine_name):
    op.add_column('output', sa.Column('coverage_ratio', sa.INTEGER(), autoincrement=False, nullable=False), schema='processing')
