"""Changing cascade action on relationships

Revision ID: 3764f1dbb49f
Revises: 8584aa2a510d
Create Date: 2017-02-02 10:07:52.534823

"""

# revision identifiers, used by Alembic.
revision = '3764f1dbb49f'
down_revision = '8584aa2a510d'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    op.drop_constraint('rel_hazardcategory_administrativ_administrativedivision_id_fkey', 'rel_hazardcategory_administrativedivision', schema='datamart', type_='foreignkey')
    op.create_foreign_key('rel_hazardcategory_administrativ_administrativedivision_id_fkey', 'rel_hazardcategory_administrativedivision', 'administrativedivision', ['administrativedivision_id'], ['id'], source_schema='datamart', referent_schema='datamart', ondelete='CASCADE')
    op.drop_constraint('rel_hazardcategory_administra_rel_hazardcategory_administr_fkey', 'rel_hazardcategory_administrativedivision_hazardset', schema='datamart', type_='foreignkey')
    op.create_foreign_key('rel_hazardcategory_administra_rel_hazardcategory_administr_fkey', 'rel_hazardcategory_administrativedivision_hazardset', 'rel_hazardcategory_administrativedivision', ['rel_hazardcategory_administrativedivision_id'], ['id'], source_schema='datamart', referent_schema='datamart', ondelete='CASCADE')
    op.drop_constraint('output_admin_id_fkey', 'output', schema='processing', type_='foreignkey')
    op.create_foreign_key('output_admin_id_fkey', 'output', 'administrativedivision', ['admin_id'], ['id'], source_schema='processing', referent_schema='datamart', ondelete='CASCADE')
    op.drop_constraint('rel_climatechangerecommendation__administrativedivision_id_fkey', 'rel_climatechangerecommendation_administrativedivision', schema='datamart', type_='foreignkey')
    op.create_foreign_key('rel_climatechangerecommendation__administrativedivision_id_fkey', 'rel_climatechangerecommendation_administrativedivision', 'administrativedivision', ['administrativedivision_id'], ['id'], source_schema='datamart', referent_schema='datamart', ondelete='CASCADE')


def downgrade(engine_name):
    op.drop_constraint('output_admin_id_fkey', 'output', schema='processing', type_='foreignkey')
    op.create_foreign_key('output_admin_id_fkey', 'output', 'administrativedivision', ['admin_id'], ['id'], source_schema='processing', referent_schema='datamart')
    op.drop_constraint('rel_hazardcategory_administrativ_administrativedivision_id_fkey', 'rel_hazardcategory_administrativedivision', schema='datamart', type_='foreignkey')
    op.drop_constraint('rel_hazardcategory_administra_rel_hazardcategory_administr_fkey', 'rel_hazardcategory_administrativedivision_hazardset', schema='datamart', type_='foreignkey')
    op.create_foreign_key('rel_hazardcategory_administra_rel_hazardcategory_administr_fkey', 'rel_hazardcategory_administrativedivision_hazardset', 'rel_hazardcategory_administrativedivision', ['rel_hazardcategory_administrativedivision_id'], ['id'], source_schema='datamart', referent_schema='datamart')
    op.create_foreign_key('rel_hazardcategory_administrativ_administrativedivision_id_fkey', 'rel_hazardcategory_administrativedivision', 'administrativedivision', ['administrativedivision_id'], ['id'], source_schema='datamart', referent_schema='datamart')
    op.drop_constraint('rel_climatechangerecommendation__administrativedivision_id_fkey', 'rel_climatechangerecommendation_administrativedivision', schema='datamart', type_='foreignkey')
    op.create_foreign_key('rel_climatechangerecommendation__administrativedivision_id_fkey', 'rel_climatechangerecommendation_administrativedivision', 'administrativedivision', ['administrativedivision_id'], ['id'], source_schema='datamart', referent_schema='datamart')
