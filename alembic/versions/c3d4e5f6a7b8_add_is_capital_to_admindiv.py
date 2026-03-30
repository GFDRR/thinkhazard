"""Add is_capital to administrativedivision

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-30 10:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    op.add_column(
        "administrativedivision",
        sa.Column("is_capital", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        schema="datamart",
    )


def downgrade(engine_name):
    op.drop_column("administrativedivision", "is_capital", schema="datamart")
