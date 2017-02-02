"""Adding fr and sp names in admin div table

Revision ID: 8584aa2a510d
Revises: d49029073f8f
Create Date: 2017-01-26 16:55:50.689618

"""

# revision identifiers, used by Alembic.
revision = '8584aa2a510d'
down_revision = 'd49029073f8f'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    op.add_column('administrativedivision', sa.Column('name_fr', sa.Unicode(), nullable=True), schema='datamart')
    op.add_column('administrativedivision', sa.Column('name_es', sa.Unicode(), nullable=True), schema='datamart')


def downgrade(engine_name):
    op.drop_column('administrativedivision', 'name_es', schema='datamart')
    op.drop_column('administrativedivision', 'name_fr', schema='datamart')
