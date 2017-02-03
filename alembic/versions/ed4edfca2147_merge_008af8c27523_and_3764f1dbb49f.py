"""Merge 008af8c27523 and 3764f1dbb49f

Revision ID: ed4edfca2147
Revises: 008af8c27523, 3764f1dbb49f
Create Date: 2017-02-03 11:38:06.286533

"""

# revision identifiers, used by Alembic.
revision = 'ed4edfca2147'
down_revision = ('008af8c27523', '3764f1dbb49f')
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    pass


def downgrade(engine_name):
    pass
