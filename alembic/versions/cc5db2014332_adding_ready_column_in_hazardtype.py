"""Adding ready column in hazardtype

Revision ID: cc5db2014332
Revises: d47e9112f635
Create Date: 2017-02-22 13:41:37.464684

"""

# revision identifiers, used by Alembic.
revision = 'cc5db2014332'
down_revision = 'd47e9112f635'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from thinkhazard.models import HazardType


def upgrade(engine_name):
    hazardtype = HazardType.__table__
    op.add_column('enum_hazardtype', sa.Column('ready', sa.Boolean(), nullable=True), schema='datamart')
    # Set all hazardtype to ready=True
    op.execute(
        hazardtype.update().values({'ready': True}))
    # Except Air Pollution
    op.execute(
        hazardtype.update().values({'ready': False})
            .where(hazardtype.c.mnemonic==op.inline_literal('AP')))


def downgrade(engine_name):
    op.drop_column('enum_hazardtype', 'ready', schema='datamart')
