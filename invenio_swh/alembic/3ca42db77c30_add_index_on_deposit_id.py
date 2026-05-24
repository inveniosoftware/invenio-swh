# SPDX-FileCopyrightText: 2016-2018 CERN.
# SPDX-License-Identifier: MIT

"""Add index on deposit id."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "3ca42db77c30"
down_revision = "f3542dda222d"
branch_labels = ()
depends_on = None


def upgrade():
    """Upgrade database."""
    op.create_index(
        op.f("ix_swh_deposit_swh_deposit_id"),
        "swh_deposit",
        ["swh_deposit_id"],
        unique=True,
    )


def downgrade():
    """Downgrade database."""
    op.drop_index(op.f("ix_swh_deposit_swh_deposit_id"), table_name="swh_deposit")
