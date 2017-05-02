"""Change distribution_url into detail_url

Revision ID: 2a26a7ae26a0
Revises: 804166ef07da
Create Date: 2017-05-02 14:29:32.674711

"""

# revision identifiers, used by Alembic.
revision = '2a26a7ae26a0'
down_revision = '804166ef07da'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    conn = op.get_bind()
    conn.execute('ALTER TABLE processing.hazardset '
                 'RENAME distribution_url TO detail_url;')


def downgrade(engine_name):
    conn = op.get_bind()
    conn.execute('ALTER TABLE processing.hazardset '
                 'RENAME detail_url TO distribution_url;')
