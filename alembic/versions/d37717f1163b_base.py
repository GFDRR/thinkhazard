"""base: First revision to mark the state when we started to use Alembic.

Revision ID: d37717f1163b
Revises: 
Create Date: 2016-04-05 18:10:00.687240

"""

# revision identifiers, used by Alembic.
revision = 'd37717f1163b'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    pass


def downgrade(engine_name):
    pass
