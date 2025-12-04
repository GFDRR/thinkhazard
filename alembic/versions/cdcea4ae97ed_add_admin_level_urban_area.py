"""Add admin level Urban area

Revision ID: cdcea4ae97ed
Revises: 33fe28fefaff
Create Date: 2025-10-08 11:40:38.482274

"""

# revision identifiers, used by Alembic.
revision = 'cdcea4ae97ed'
down_revision = 'f875f378cb13'
branch_labels = None
depends_on = None

from alembic import op
from thinkhazard.models import AdminLevelType


def upgrade(engine_name):
    adminleveltype = AdminLevelType.__table__

    op.execute(
        adminleveltype.insert() \
            .values({'mnemonic': op.inline_literal('URB'),
                     'title': op.inline_literal('Urban area'),
                     'description': op.inline_literal('Urban area')}))


def downgrade(engine_name):
    adminleveltype = AdminLevelType.__table__

    op.execute(
        adminleveltype.delete() \
            .where(adminleveltype.c.mnemonic==op.inline_literal('URB')))
