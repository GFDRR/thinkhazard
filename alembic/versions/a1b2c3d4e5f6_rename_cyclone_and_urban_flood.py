# -*- coding: utf-8 -*-
"""Rename Cyclone to Tropical cyclone and Urban flood to Pluvial flood

Revision ID: a1b2c3d4e5f6
Revises: 50e54a034fa5
Create Date: 2026-01-05 12:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "50e54a034fa5"
branch_labels = None
depends_on = None

from alembic import op
from thinkhazard.models import HazardType


def upgrade(engine_name):
    hazardtype = HazardType.__table__

    # Rename "Cyclone" to "Tropical cyclone" and change mnemonic CY -> TC
    op.execute(
        hazardtype.update()
        .where(hazardtype.c.mnemonic == op.inline_literal("CY"))
        .values(
            {
                "mnemonic": op.inline_literal("TC"),
                "title": op.inline_literal("Tropical cyclone"),
            }
        )
    )

    # Rename "Urban flood" to "Pluvial flood" and change mnemonic UF -> PF
    op.execute(
        hazardtype.update()
        .where(hazardtype.c.mnemonic == op.inline_literal("UF"))
        .values(
            {
                "mnemonic": op.inline_literal("PF"),
                "title": op.inline_literal("Pluvial flood"),
            }
        )
    )


def downgrade(engine_name):
    hazardtype = HazardType.__table__

    # Revert "Tropical cyclone" back to "Cyclone" and mnemonic TC -> CY
    op.execute(
        hazardtype.update()
        .where(hazardtype.c.mnemonic == op.inline_literal("TC"))
        .values(
            {"mnemonic": op.inline_literal("CY"), "title": op.inline_literal("Cyclone")}
        )
    )

    # Revert "Pluvial flood" back to "Urban flood" and mnemonic PF -> UF
    op.execute(
        hazardtype.update()
        .where(hazardtype.c.mnemonic == op.inline_literal("PF"))
        .values(
            {
                "mnemonic": op.inline_literal("UF"),
                "title": op.inline_literal("Urban flood"),
            }
        )
    )
