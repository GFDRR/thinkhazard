"""Merge 8f08766e4541 and 7f0c2b165740

Revision ID: 19c37eae5bb2
Revises: 8f08766e4541, 7f0c2b165740
Create Date: 2017-06-01 13:08:50.673065

"""

# revision identifiers, used by Alembic.
revision = '19c37eae5bb2'
down_revision = ('8f08766e4541', '7f0c2b165740')
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    pass


def downgrade(engine_name):
    pass
