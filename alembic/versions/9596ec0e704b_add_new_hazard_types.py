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
                     'title': op.inline_literal('Urban flood'),
                     'order': 2}))
    op.execute(
        hazardtype.insert() \
            .values({'mnemonic': op.inline_literal('EH'),
                     'title': op.inline_literal('Extreme heat'),
                     'order': 10}))
    op.execute(
        hazardtype.insert() \
            .values({'mnemonic': op.inline_literal('WF'),
                     'title': op.inline_literal('Wildfire'),
                     'order': 11}))
    op.execute(
        hazardtype.insert() \
            .values({'mnemonic': op.inline_literal('AP'),
                     'title': op.inline_literal('Air pollution'),
                     'order': 12}))
    op.execute(
        hazardtype.update().values({'order': 3}) \
            .where(hazardtype.c.mnemonic==op.inline_literal('CF')))
    op.execute(
        hazardtype.update().values({'order': 4}) \
            .where(hazardtype.c.mnemonic==op.inline_literal('EQ')))
    op.execute(
        hazardtype.update().values({'order': 5}) \
            .where(hazardtype.c.mnemonic==op.inline_literal('LS')))
    op.execute(
        hazardtype.update().values({'order': 6}) \
            .where(hazardtype.c.mnemonic==op.inline_literal('TS')))
    op.execute(
        hazardtype.update().values({'order': 7}) \
            .where(hazardtype.c.mnemonic==op.inline_literal('VO')))
    op.execute(
        hazardtype.update().values({'order': 8}) \
            .where(hazardtype.c.mnemonic==op.inline_literal('CY')))
    op.execute(
        hazardtype.update().values({'order': 9}) \
            .where(hazardtype.c.mnemonic==op.inline_literal('DG')))
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
