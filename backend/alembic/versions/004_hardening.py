"""Migration — idempotência, trace_id e hardening."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_hardening"
down_revision: Union[str, None] = "003_telemetry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("positions", sa.Column("trace_id", sa.String(length=36), nullable=True))
    op.create_index(op.f("ix_positions_trace_id"), "positions", ["trace_id"])

    op.add_column("device_events", sa.Column("trace_id", sa.String(length=36), nullable=True))
    op.create_index(op.f("ix_device_events_trace_id"), "device_events", ["trace_id"])

    op.create_table(
        "processed_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dedup_key", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=False),
        sa.Column("tracker_imei", sa.String(length=20), nullable=False),
        sa.Column("message_type", sa.String(length=20), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_key"),
    )
    op.create_index("ix_processed_events_imei", "processed_events", ["tracker_imei"])


def downgrade() -> None:
    op.drop_index("ix_processed_events_imei", table_name="processed_events")
    op.drop_table("processed_events")
    op.drop_index(op.f("ix_device_events_trace_id"), table_name="device_events")
    op.drop_column("device_events", "trace_id")
    op.drop_index(op.f("ix_positions_trace_id"), table_name="positions")
    op.drop_column("positions", "trace_id")
