"""Added relation between layers and regions

Revision ID: 9b6c686138eb
Revises: cc5db2014332
Create Date: 2017-03-02 10:31:13.595702

"""

# revision identifiers, used by Alembic.
revision = '9b6c686138eb'
down_revision = 'cc5db2014332'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    op.create_table(
        'rel_hazardset_region',
        sa.Column('hazardset_id', sa.String(), nullable=True),
        sa.Column('region_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['hazardset_id'], ['processing.hazardset.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['region_id'], ['datamart.enum_region.id'], ondelete='CASCADE'),
        schema='processing'
    )


def downgrade(engine_name):
    op.drop_table('rel_hazardset_region', schema='processing')
