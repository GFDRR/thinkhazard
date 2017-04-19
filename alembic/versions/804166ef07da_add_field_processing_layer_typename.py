"""Add field processing.layer.typename

Revision ID: 804166ef07da
Revises: 967e9eaaed70
Create Date: 2017-04-19 11:50:32.337522

"""

# revision identifiers, used by Alembic.
revision = '804166ef07da'
down_revision = '967e9eaaed70'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    op.add_column('layer', sa.Column('typename', sa.String(), nullable=True), schema='processing')
    op.create_unique_constraint(None, 'layer', ['typename'], schema='processing')


def downgrade(engine_name):
    op.drop_constraint(None, 'layer', schema='processing', type_='unique')
    op.drop_column('layer', 'typename', schema='processing')
