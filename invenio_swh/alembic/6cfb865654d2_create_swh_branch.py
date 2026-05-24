# SPDX-FileCopyrightText: 2016-2018 CERN.
# SPDX-License-Identifier: MIT

"""create swh branch."""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6cfb865654d2"
down_revision = None
branch_labels = ("invenio_swh",)
depends_on = "dbdbc1b19cf2"


def upgrade():
    """Upgrade database."""
    pass


def downgrade():
    """Downgrade database."""
    pass
