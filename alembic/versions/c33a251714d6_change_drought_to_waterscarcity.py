"""empty message

Revision ID: c33a251714d6
Revises: d37717f1163b
Create Date: 2016-04-08 11:24:51.748011

"""

# revision identifiers, used by Alembic.
revision = 'c33a251714d6'
down_revision = 'd37717f1163b'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from thinkhazard.models import HazardType


def upgrade(engine_name):
    hazardtype = HazardType.__table__

    op.execute(
        hazardtype.update() \
            .where(hazardtype.c.mnemonic==op.inline_literal('DG')) \
            .values({'title': op.inline_literal('Water scarcity')}))
    pass


def downgrade(engine_name):
    hazardtype = HazardType.__table__

    op.execute(
        hazardtype.update() \
            .where(hazardtype.c.mnemonic==op.inline_literal('DG')) \
            .values({'title': op.inline_literal('Drought')}))
    pass
