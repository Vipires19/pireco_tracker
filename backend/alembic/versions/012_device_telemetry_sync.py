"""Migration — Device telemetry sync fields (protocol + last GPS snapshot)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_device_telemetry_sync"
down_revision: Union[str, None] = "011_trackers_imei_partial_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("trackers", sa.Column("protocol", sa.String(length=50), nullable=True))
    op.add_column("trackers", sa.Column("last_latitude", sa.Float(), nullable=True))
    op.add_column("trackers", sa.Column("last_longitude", sa.Float(), nullable=True))
    op.add_column("trackers", sa.Column("last_speed", sa.Float(), nullable=True))
    op.add_column("trackers", sa.Column("last_course", sa.Integer(), nullable=True))
    op.add_column(
        "trackers",
        sa.Column("last_gps_time", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("trackers", "last_gps_time")
    op.drop_column("trackers", "last_course")
    op.drop_column("trackers", "last_speed")
    op.drop_column("trackers", "last_longitude")
    op.drop_column("trackers", "last_latitude")
    op.drop_column("trackers", "protocol")
