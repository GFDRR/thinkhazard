"""Add Extreme Heat hazard categories

Revision ID: 967e9eaaed70
Revises: 9b6c686138eb
Create Date: 2017-03-03 11:41:50.906305

"""

# revision identifiers, used by Alembic.
revision = '967e9eaaed70'
down_revision = '9b6c686138eb'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from thinkhazard.models import HazardType, HazardCategory, HazardLevel

hazardtype = HazardType.__table__
hazardlevel = HazardLevel.__table__
hazardcategory = HazardCategory.__table__

def upgrade(engine_name):

    for level in ['VLO', 'LOW', 'MED', 'HIG']:
        op.execute(hazardcategory.insert().values(
            hazardtype_id=sa.select(
                [hazardtype.c.id],
                hazardtype.c.mnemonic==op.inline_literal('EH')
            ),
            hazardlevel_id=sa.select(
                [hazardlevel.c.id],
                hazardlevel.c.mnemonic==op.inline_literal(level)
            ),
            general_recommendation=op.inline_literal(
                'General recommendation for EH %s' % level)
        ))
    pass


def downgrade(engine_name):
    op.execute(hazardcategory.delete().where(
        hazardcategory.c.hazardtype_id==sa.select(
            [hazardtype.c.id],
            hazardtype.c.mnemonic==op.inline_literal('EH')
        )
    ))
    pass
