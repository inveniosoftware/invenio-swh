#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Increase identifier string length."""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f3542dda222d"
down_revision = "ed8813bfcb2b"
branch_labels = ()
depends_on = None


def upgrade():
    """Upgrade database."""
    op.alter_column(
        "swh_deposit",
        "swhid",
        existing_type=sa.String(length=255),
        type_=sa.String(length=1024),
        existing_nullable=True,
    )


def downgrade():
    """Downgrade database."""
    op.alter_column(
        "swh_deposit",
        "swhid",
        existing_type=sa.String(length=1024),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
