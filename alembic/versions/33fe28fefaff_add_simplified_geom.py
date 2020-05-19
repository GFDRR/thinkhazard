"""Add simplified_geom

Revision ID: 33fe28fefaff
Revises: 19c37eae5bb2
Create Date: 2020-05-14 12:35:28.987096

"""

# revision identifiers, used by Alembic.
revision = '33fe28fefaff'
down_revision = '19c37eae5bb2'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
import geoalchemy2
from pkg_resources import resource_string


def upgrade(engine_name):
    op.add_column('administrativedivision', sa.Column('geom_simplified', geoalchemy2.types.Geometry(geometry_type='MULTIPOLYGON', srid=3857), nullable=True), schema='datamart')
    op.add_column('administrativedivision', sa.Column('geom_simplified_for_parent', geoalchemy2.types.Geometry(geometry_type='MULTIPOLYGON', srid=3857), nullable=True), schema='datamart')
    conn = op.get_bind()
    conn.execute(sa.text(
        resource_string("thinkhazard", "scripts/simplify.sql").decode("utf8")
    ))


def downgrade(engine_name):
    op.drop_column('administrativedivision', 'geom_simplified', schema='datamart')
    op.drop_column('administrativedivision', 'geom_simplified_for_parent', schema='datamart')
