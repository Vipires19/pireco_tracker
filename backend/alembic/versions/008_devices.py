"""Migration — Devices domain (trackers ERP schema)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_devices"
down_revision: Union[str, None] = "007_fleet"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- trackers: novos campos ERP (mantém colunas legadas para o Worker) ---
    op.add_column("trackers", sa.Column("manufacturer", sa.String(length=100), nullable=True))
    op.add_column("trackers", sa.Column("firmware", sa.String(length=100), nullable=True))
    op.add_column("trackers", sa.Column("tracker_phone_number", sa.String(length=20), nullable=True))
    op.add_column("trackers", sa.Column("sim_iccid", sa.String(length=22), nullable=True))
    op.add_column("trackers", sa.Column("sim_imei", sa.String(length=20), nullable=True))
    op.add_column("trackers", sa.Column("carrier", sa.String(length=100), nullable=True))
    op.add_column("trackers", sa.Column("apn", sa.String(length=100), nullable=True))
    op.add_column("trackers", sa.Column("serial_number", sa.String(length=100), nullable=True))
    op.add_column("trackers", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "trackers",
        sa.Column("status", sa.String(length=30), nullable=True, server_default="IN_STOCK"),
    )
    op.add_column(
        "trackers",
        sa.Column("health_status", sa.String(length=20), nullable=True, server_default="UNKNOWN"),
    )
    op.add_column("trackers", sa.Column("last_ip", sa.String(length=45), nullable=True))
    op.add_column("trackers", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        sa.text("UPDATE trackers SET last_ip = last_remote_ip WHERE last_ip IS NULL AND last_remote_ip IS NOT NULL")
    )
    op.execute(
        sa.text(
            "UPDATE trackers SET status = CASE WHEN is_active THEN 'INSTALLED' ELSE 'IN_STOCK' END "
            "WHERE status IS NULL"
        )
    )

    op.alter_column("trackers", "status", nullable=False, server_default="IN_STOCK")
    op.alter_column("trackers", "health_status", nullable=False, server_default="UNKNOWN")

    op.create_index(op.f("ix_trackers_status"), "trackers", ["status"], unique=False)
    op.create_index(op.f("ix_trackers_health_status"), "trackers", ["health_status"], unique=False)
    op.create_index(
        op.f("ix_trackers_tracker_phone_number"), "trackers", ["tracker_phone_number"], unique=False
    )
    op.create_index(op.f("ix_trackers_sim_iccid"), "trackers", ["sim_iccid"], unique=False)
    op.create_index(op.f("ix_trackers_sim_imei"), "trackers", ["sim_imei"], unique=False)
    op.create_index(op.f("ix_trackers_serial_number"), "trackers", ["serial_number"], unique=False)

    # --- tracker_assignments: histórico de instalação (mantém colunas legadas para o Worker) ---
    op.add_column(
        "tracker_assignments",
        sa.Column(
            "installed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column("tracker_assignments", sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tracker_assignments", sa.Column("installed_by", sa.Integer(), nullable=True))
    op.add_column("tracker_assignments", sa.Column("removed_by", sa.Integer(), nullable=True))
    op.add_column("tracker_assignments", sa.Column("removal_reason", sa.Text(), nullable=True))
    op.add_column(
        "tracker_assignments",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )
    op.add_column(
        "tracker_assignments",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )

    op.execute(
        sa.text(
            "UPDATE tracker_assignments SET installed_at = assigned_at WHERE installed_at IS NULL"
        )
    )
    op.execute(
        sa.text(
            "UPDATE tracker_assignments SET removed_at = unassigned_at "
            "WHERE removed_at IS NULL AND unassigned_at IS NOT NULL"
        )
    )
    op.execute(
        sa.text(
            "UPDATE tracker_assignments SET created_at = assigned_at WHERE created_at IS NULL"
        )
    )
    op.execute(
        sa.text(
            "UPDATE tracker_assignments SET updated_at = COALESCE(unassigned_at, assigned_at) "
            "WHERE updated_at IS NULL"
        )
    )

    op.alter_column("tracker_assignments", "installed_at", nullable=False)
    op.alter_column("tracker_assignments", "created_at", nullable=False)
    op.alter_column("tracker_assignments", "updated_at", nullable=False)

    op.create_foreign_key(
        "fk_tracker_assignments_installed_by",
        "tracker_assignments",
        "users",
        ["installed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_tracker_assignments_removed_by",
        "tracker_assignments",
        "users",
        ["removed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_tracker_assignments_installed_by"),
        "tracker_assignments",
        ["installed_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tracker_assignments_removed_by"), "tracker_assignments", ["removed_by"], unique=False
    )

    op.create_table(
        "tracker_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tracker_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tracker_id"], ["trackers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tracker_audit_logs_tracker_id"), "tracker_audit_logs", ["tracker_id"], unique=False
    )
    op.create_index(
        op.f("ix_tracker_audit_logs_user_id"), "tracker_audit_logs", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_tracker_audit_logs_action"), "tracker_audit_logs", ["action"], unique=False
    )
    op.create_index(
        op.f("ix_tracker_audit_logs_created_at"),
        "tracker_audit_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tracker_audit_logs_created_at"), table_name="tracker_audit_logs")
    op.drop_index(op.f("ix_tracker_audit_logs_action"), table_name="tracker_audit_logs")
    op.drop_index(op.f("ix_tracker_audit_logs_user_id"), table_name="tracker_audit_logs")
    op.drop_index(op.f("ix_tracker_audit_logs_tracker_id"), table_name="tracker_audit_logs")
    op.drop_table("tracker_audit_logs")

    op.drop_index(op.f("ix_tracker_assignments_removed_by"), table_name="tracker_assignments")
    op.drop_index(op.f("ix_tracker_assignments_installed_by"), table_name="tracker_assignments")
    op.drop_constraint("fk_tracker_assignments_removed_by", "tracker_assignments", type_="foreignkey")
    op.drop_constraint("fk_tracker_assignments_installed_by", "tracker_assignments", type_="foreignkey")
    op.drop_column("tracker_assignments", "updated_at")
    op.drop_column("tracker_assignments", "created_at")
    op.drop_column("tracker_assignments", "removal_reason")
    op.drop_column("tracker_assignments", "removed_by")
    op.drop_column("tracker_assignments", "installed_by")
    op.drop_column("tracker_assignments", "removed_at")
    op.drop_column("tracker_assignments", "installed_at")

    op.drop_index(op.f("ix_trackers_serial_number"), table_name="trackers")
    op.drop_index(op.f("ix_trackers_sim_imei"), table_name="trackers")
    op.drop_index(op.f("ix_trackers_sim_iccid"), table_name="trackers")
    op.drop_index(op.f("ix_trackers_tracker_phone_number"), table_name="trackers")
    op.drop_index(op.f("ix_trackers_health_status"), table_name="trackers")
    op.drop_index(op.f("ix_trackers_status"), table_name="trackers")
    op.drop_column("trackers", "deleted_at")
    op.drop_column("trackers", "last_ip")
    op.drop_column("trackers", "health_status")
    op.drop_column("trackers", "status")
    op.drop_column("trackers", "notes")
    op.drop_column("trackers", "serial_number")
    op.drop_column("trackers", "apn")
    op.drop_column("trackers", "carrier")
    op.drop_column("trackers", "sim_imei")
    op.drop_column("trackers", "sim_iccid")
    op.drop_column("trackers", "tracker_phone_number")
    op.drop_column("trackers", "firmware")
    op.drop_column("trackers", "manufacturer")
