"""Migration — Installations domain (tracker_assignments ERP fields)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_installations"
down_revision: Union[str, None] = "009_devices_origin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tracker_assignments",
        sa.Column("installation_type", sa.String(length=20), nullable=True, server_default="PRIMARY"),
    )
    op.add_column(
        "tracker_assignments",
        sa.Column("status", sa.String(length=20), nullable=True, server_default="PENDING"),
    )
    op.add_column("tracker_assignments", sa.Column("installation_notes", sa.Text(), nullable=True))
    op.add_column(
        "tracker_assignments",
        sa.Column("power_connected", sa.Boolean(), nullable=True, server_default=sa.text("false")),
    )
    op.add_column(
        "tracker_assignments",
        sa.Column("gps_ok", sa.Boolean(), nullable=True, server_default=sa.text("false")),
    )
    op.add_column(
        "tracker_assignments",
        sa.Column("gsm_ok", sa.Boolean(), nullable=True, server_default=sa.text("false")),
    )
    op.add_column(
        "tracker_assignments",
        sa.Column("ignition_ok", sa.Boolean(), nullable=True, server_default=sa.text("false")),
    )
    op.add_column(
        "tracker_assignments",
        sa.Column("blocking_ok", sa.Boolean(), nullable=True, server_default=sa.text("false")),
    )
    op.add_column(
        "tracker_assignments",
        sa.Column("test_drive_completed", sa.Boolean(), nullable=True, server_default=sa.text("false")),
    )
    op.add_column(
        "tracker_assignments",
        sa.Column("customer_present", sa.Boolean(), nullable=True, server_default=sa.text("false")),
    )

    op.execute(
        sa.text(
            "UPDATE tracker_assignments SET status = 'INSTALLED', installation_type = 'PRIMARY' "
            "WHERE removed_at IS NULL"
        )
    )
    op.execute(
        sa.text(
            "UPDATE tracker_assignments SET status = 'REMOVED', installation_type = 'PRIMARY' "
            "WHERE removed_at IS NOT NULL"
        )
    )

    op.alter_column("tracker_assignments", "installation_type", nullable=False, server_default="PRIMARY")
    op.alter_column("tracker_assignments", "status", nullable=False, server_default="PENDING")
    op.alter_column("tracker_assignments", "power_connected", nullable=False, server_default=sa.text("false"))
    op.alter_column("tracker_assignments", "gps_ok", nullable=False, server_default=sa.text("false"))
    op.alter_column("tracker_assignments", "gsm_ok", nullable=False, server_default=sa.text("false"))
    op.alter_column("tracker_assignments", "ignition_ok", nullable=False, server_default=sa.text("false"))
    op.alter_column("tracker_assignments", "blocking_ok", nullable=False, server_default=sa.text("false"))
    op.alter_column("tracker_assignments", "test_drive_completed", nullable=False, server_default=sa.text("false"))
    op.alter_column("tracker_assignments", "customer_present", nullable=False, server_default=sa.text("false"))

    op.create_index(
        op.f("ix_tracker_assignments_installation_type"),
        "tracker_assignments",
        ["installation_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tracker_assignments_status"),
        "tracker_assignments",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tracker_assignments_status"), table_name="tracker_assignments")
    op.drop_index(op.f("ix_tracker_assignments_installation_type"), table_name="tracker_assignments")
    op.drop_column("tracker_assignments", "customer_present")
    op.drop_column("tracker_assignments", "test_drive_completed")
    op.drop_column("tracker_assignments", "blocking_ok")
    op.drop_column("tracker_assignments", "ignition_ok")
    op.drop_column("tracker_assignments", "gsm_ok")
    op.drop_column("tracker_assignments", "gps_ok")
    op.drop_column("tracker_assignments", "power_connected")
    op.drop_column("tracker_assignments", "installation_notes")
    op.drop_column("tracker_assignments", "status")
    op.drop_column("tracker_assignments", "installation_type")
