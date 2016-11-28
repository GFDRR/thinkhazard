"""Add new hazard types

Revision ID: 9596ec0e704b
Revises: d49029073f8f
Create Date: 2016-11-28 15:14:40.766412

"""

# revision identifiers, used by Alembic.
revision = '9596ec0e704b'
down_revision = 'd49029073f8f'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from thinkhazard.models import HazardType


def upgrade(engine_name):
    hazardtype = HazardType.__table__

    op.execute(
        hazardtype.insert() \
            .values({'mnemonic': op.inline_literal('UF'),
                     'title': op.inline_literal('Urban flood')}))
    op.execute(
        hazardtype.insert() \
            .values({'mnemonic': op.inline_literal('EH'),
                     'title': op.inline_literal('Extreme heat')}))
    op.execute(
        hazardtype.insert() \
            .values({'mnemonic': op.inline_literal('WF'),
                     'title': op.inline_literal('Wildfire')}))
    op.execute(
        hazardtype.insert() \
            .values({'mnemonic': op.inline_literal('AP'),
                     'title': op.inline_literal('Air pollution')}))
    pass


def downgrade(engine_name):
    hazardtype = HazardType.__table__

    op.execute(
        hazardtype.delete() \
            .where(hazardtype.c.mnemonic==op.inline_literal('UF')))
    op.execute(
        hazardtype.delete() \
            .where(hazardtype.c.mnemonic==op.inline_literal('EH')))
    op.execute(
        hazardtype.delete() \
            .where(hazardtype.c.mnemonic==op.inline_literal('WF')))
    op.execute(
        hazardtype.delete() \
            .where(hazardtype.c.mnemonic==op.inline_literal('AP')))
    pass
