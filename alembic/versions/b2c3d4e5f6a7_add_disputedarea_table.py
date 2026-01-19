# -*- coding: utf-8 -*-
"""Add disputedarea table for NDLSA (Non-determined legal status areas)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-14 10:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "345f4b2e2934"
branch_labels = None
depends_on = None

import geoalchemy2
import sqlalchemy as sa
from alembic import op


def upgrade(engine_name):
    op.create_table(
        "disputedarea",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Unicode(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(geometry_type="MULTIPOLYGON", srid=4326),
            nullable=True,
        ),
        sa.Column(
            "geom_simplified",
            geoalchemy2.types.Geometry(geometry_type="MULTIPOLYGON", srid=3857),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="datamart",
    )


def downgrade(engine_name):
    op.drop_table("disputedarea", schema="datamart")
