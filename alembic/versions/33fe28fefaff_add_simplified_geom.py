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


def upgrade(engine_name):
    op.add_column('administrativedivision', sa.Column('geom_simplified', geoalchemy2.types.Geometry(geometry_type='MULTIPOLYGON', srid=3857), nullable=True), schema='datamart')
    conn = op.get_bind()
    conn.execute('''
UPDATE datamart.administrativedivision
SET geom_simplified = ST_Simplify(
    ST_Transform(geom, 3857),
    ST_DistanceSphere(
        ST_Point(ST_XMin(geom), ST_YMin(geom)),
        ST_Point(ST_XMax(geom), ST_YMax(geom))
    ) / 250
);
''')


def downgrade(engine_name):
    op.drop_column('administrativedivision', 'simplified_geom', schema='datamart')
