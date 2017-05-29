"""Add category for Urban Flood, Wild Fire & Air Pollution

Revision ID: 8f08766e4541
Revises: 2a26a7ae26a0
Create Date: 2017-05-29 12:24:46.523502

"""

# revision identifiers, used by Alembic.
revision = '8f08766e4541'
down_revision = '2a26a7ae26a0'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from thinkhazard.models import HazardType, HazardCategory, HazardLevel

hazardtype = HazardType.__table__
hazardlevel = HazardLevel.__table__
hazardcategory = HazardCategory.__table__

def upgrade(engine_name):

    for htype in ['UF', 'WF', 'AP']:
        for level in ['VLO', 'LOW', 'MED', 'HIG']:
            op.execute(hazardcategory.insert().values(
                hazardtype_id=sa.select(
                    [hazardtype.c.id],
                    hazardtype.c.mnemonic==op.inline_literal(htype)
                ),
                hazardlevel_id=sa.select(
                    [hazardlevel.c.id],
                    hazardlevel.c.mnemonic==op.inline_literal(level)
                ),
                general_recommendation=op.inline_literal(
                    'General recommendation for %s %s' % (htype, level))
            ))


def downgrade(engine_name):
    for htype in ['UF', 'WF', 'AP']:
        op.execute(hazardcategory.delete().where(
            hazardcategory.c.hazardtype_id==sa.select(
                [hazardtype.c.id],
                hazardtype.c.mnemonic==op.inline_literal(htype)
            )
        ))
