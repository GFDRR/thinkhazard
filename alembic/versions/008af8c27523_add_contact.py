"""Add contact

Revision ID: 008af8c27523
Revises: d49029073f8f
Create Date: 2016-12-07 10:17:54.154799

"""

# revision identifiers, used by Alembic.
revision = '008af8c27523'
down_revision = 'd49029073f8f'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    op.create_table('contact',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Unicode(), nullable=True),
    sa.Column('url', sa.Unicode(), nullable=True),
    sa.Column('phone', sa.Unicode(), nullable=True),
    sa.Column('email', sa.Unicode(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    schema='datamart'
    )
    op.create_table('rel_contact_administrativedivision_hazardtype',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('contact_id', sa.Integer(), nullable=False),
    sa.Column('administrativedivision_id', sa.Integer(), nullable=False),
    sa.Column('hazardtype_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['administrativedivision_id'], ['datamart.administrativedivision.id'], ),
    sa.ForeignKeyConstraint(['contact_id'], ['datamart.contact.id'], ),
    sa.ForeignKeyConstraint(['hazardtype_id'], ['datamart.enum_hazardtype.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='datamart'
    )
    op.create_index(op.f('ix_datamart_rel_contact_administrativedivision_hazardtype_contact_id'), 'rel_contact_administrativedivision_hazardtype', ['contact_id'], unique=False, schema='datamart')
    op.create_index(op.f('ix_datamart_rel_contact_administrativedivision_hazardtype_hazardtype_id'), 'rel_contact_administrativedivision_hazardtype', ['hazardtype_id'], unique=False, schema='datamart')


def downgrade(engine_name):
    op.drop_index(op.f('ix_datamart_rel_contact_administrativedivision_hazardtype_hazardtype_id'), table_name='rel_contact_administrativedivision_hazardtype', schema='datamart')
    op.drop_index(op.f('ix_datamart_rel_contact_administrativedivision_hazardtype_contact_id'), table_name='rel_contact_administrativedivision_hazardtype', schema='datamart')
    op.drop_table('rel_contact_administrativedivision_hazardtype', schema='datamart')
    op.drop_table('contact', schema='datamart')
