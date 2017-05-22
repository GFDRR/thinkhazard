"""Add column hazardset.processing_error

Revision ID: 7f0c2b165740
Revises: 2a26a7ae26a0
Create Date: 2017-05-22 16:17:40.677104

"""

# revision identifiers, used by Alembic.
revision = '7f0c2b165740'
down_revision = '2a26a7ae26a0'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    op.add_column('hazardset', sa.Column('processing_error', sa.String(), nullable=True), schema='processing')


def downgrade(engine_name):
    op.drop_column('hazardset', 'processing_error', schema='processing')
