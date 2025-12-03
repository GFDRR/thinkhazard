"""Convert admindiv.code to string

Revision ID: f875f378cb13
Revises: cdcea4ae97ed
Create Date: 2025-12-01 10:50:49.764473

"""

# revision identifiers, used by Alembic.
revision = 'f875f378cb13'
down_revision = '33fe28fefaff'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    # Drop the foreign key constraint first
    op.drop_constraint(
        'administrativedivision_parent_code_fkey',
        'administrativedivision',
        schema='datamart',
        type_='foreignkey'
    )

    # Modify the columns
    op.alter_column(
        'administrativedivision',
        'code',
        existing_type=sa.INTEGER(),
        type_=sa.String(),
        existing_nullable=False,
        schema='datamart',
    )
    op.alter_column(
        'administrativedivision',
        'parent_code',
        existing_type=sa.INTEGER(),
        type_=sa.String(),
        existing_nullable=True,
        schema='datamart',
    )

    # Recreate the foreign key constraint
    op.create_foreign_key(
        'administrativedivision_parent_code_fkey',
        'administrativedivision',
        'administrativedivision', 
        ['parent_code'],
        ['code'],
        source_schema='datamart',
        referent_schema='datamart',
    )

def downgrade(engine_name):
    # Drop the foreign key constraint first
    op.drop_constraint(
        'administrativedivision_parent_code_fkey',
        'administrativedivision',
        schema='datamart',
        type_='foreignkey',
    )

    # Modify the columns back to integer
    op.alter_column(
        'administrativedivision',
        'parent_code',
        existing_type=sa.String(),
        type_=sa.INTEGER(),
        existing_nullable=True,
        schema='datamart',
    )
    op.alter_column(
        'administrativedivision',
        'code',
        existing_type=sa.String(),
        type_=sa.INTEGER(),
        existing_nullable=False,
        schema='datamart',
    )

    # Recreate the foreign key constraint with integer types
    op.create_foreign_key(
        'administrativedivision_parent_code_fkey',
        'administrativedivision',
        'administrativedivision', 
        ['parent_code'],
        ['code'],
        source_schema='datamart',
        referent_schema='datamart',
    )
