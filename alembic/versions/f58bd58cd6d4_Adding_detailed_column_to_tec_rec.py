"""Adding detail column to tech rec

Revision ID: f58bd58cd6d4
Revises: 06bbf407cad3
Create Date: 2016-04-07 16:59:58.502602

"""

# revision identifiers, used by Alembic.
revision = 'f58bd58cd6d4'
down_revision = '06bbf407cad3'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    op.add_column('technicalrecommendation', sa.Column('detail', sa.Unicode(),
                  nullable=True), schema='datamart')


def downgrade(engine_name):
    op.drop_column('technicalrecommendation', 'detail', schema='datamart')
