"""add name_en

Revision ID: 345f4b2e2934
Revises: a1b2c3d4e5f6
Create Date: 2026-01-08 13:46:40.294080

"""

# revision identifiers, used by Alembic.
revision = "345f4b2e2934"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    op.add_column(
        "administrativedivision",
        sa.Column("name_en", sa.Unicode(), nullable=True),
        schema="datamart",
    )


def downgrade(engine_name):
    op.drop_column("administrativedivision", "name_en", schema="datamart")
