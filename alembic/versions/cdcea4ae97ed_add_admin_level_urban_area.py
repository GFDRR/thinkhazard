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

import sqlalchemy as sa
from alembic import op
from thinkhazard.models import AdminLevelType, AdministrativeDivision


def upgrade(engine_name):
    adminleveltype = AdminLevelType.__table__

    op.execute(
        adminleveltype.insert() \
            .values({'id': 4,
                     'mnemonic': op.inline_literal('URB'),
                     'title': op.inline_literal('Urban area'),
                     'description': op.inline_literal('Urban area')}))

    op.execute(
        sa.text(
            """
            SELECT setval(
                pg_get_serial_sequence('datamart.enum_adminleveltype', 'id'),
                4
            );
            """
        )
    )


def downgrade(engine_name):
    adminleveltype = AdminLevelType.__table__

    op.execute(
        adminleveltype.delete() \
            .where(adminleveltype.c.mnemonic==op.inline_literal('URB')))

    op.execute(
        sa.text(
            """
            SELECT setval(
                pg_get_serial_sequence('datamart.enum_adminleveltype', 'id'),
                3
            );
            """
        )
    )
