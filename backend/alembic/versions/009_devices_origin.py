"""Migration — Devices domain (tracker origin field)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_devices_origin"
down_revision: Union[str, None] = "008_devices"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trackers",
        sa.Column("origin", sa.String(length=20), nullable=True, server_default="MANUAL"),
    )
    op.execute(sa.text("UPDATE trackers SET origin = 'MANUAL' WHERE origin IS NULL"))
    op.alter_column("trackers", "origin", nullable=False, server_default="MANUAL")
    op.create_index(op.f("ix_trackers_origin"), "trackers", ["origin"], unique=False)

    # Legacy multi-tenant column kept for the Worker (migration 002). It is NOT NULL
    # and unmapped by the ERP ORM model, so give it a server default to allow inserts.
    op.execute(sa.text("UPDATE trackers SET company_id = 1 WHERE company_id IS NULL"))
    op.alter_column("trackers", "company_id", server_default="1")


def downgrade() -> None:
    op.alter_column("trackers", "company_id", server_default=None)
    op.drop_index(op.f("ix_trackers_origin"), table_name="trackers")
    op.drop_column("trackers", "origin")
