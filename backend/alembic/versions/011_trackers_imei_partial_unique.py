"""Migration — Partial unique index on trackers.imei for soft delete."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_trackers_imei_partial_unique"
down_revision: Union[str, None] = "010_installations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("ix_trackers_imei"), table_name="trackers")
    op.create_index(
        "uq_trackers_imei_active",
        "trackers",
        ["imei"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    # Índice não-único para lookups por IMEI (inclui soft-deleted).
    op.create_index(op.f("ix_trackers_imei"), "trackers", ["imei"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_trackers_imei"), table_name="trackers")
    op.drop_index("uq_trackers_imei_active", table_name="trackers")
    op.create_index(op.f("ix_trackers_imei"), "trackers", ["imei"], unique=True)
