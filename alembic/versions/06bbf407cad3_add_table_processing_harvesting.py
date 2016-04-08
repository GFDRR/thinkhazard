"""Add table processing.harvesting

Revision ID: 06bbf407cad3
Revises: d37717f1163b
Create Date: 2016-04-08 13:41:54.578529

"""

# revision identifiers, used by Alembic.
revision = '06bbf407cad3'
down_revision = 'c33a251714d6'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    op.create_table('harvesting',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('complete', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    schema='processing'
    )


def downgrade(engine_name):
    op.drop_table('harvesting', schema='processing')
