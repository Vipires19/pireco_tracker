"""Telemetry tables — Fleet, Position, DeviceEvent."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "003_telemetry"
down_revision: Union[str, None] = "002_multi_tenant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fleets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fleets_company_id"), "fleets", ["company_id"])

    op.add_column("vehicles", sa.Column("fleet_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_vehicles_fleet_id", "vehicles", "fleets", ["fleet_id"], ["id"])
    op.create_index(op.f("ix_vehicles_fleet_id"), "vehicles", ["fleet_id"])

    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tracker_id", sa.Integer(), nullable=False),
        sa.Column("tracker_imei", sa.String(length=20), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("speed_kmh", sa.Float(), nullable=True),
        sa.Column("course_degrees", sa.Integer(), nullable=True),
        sa.Column("gps_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("connection_id", sa.String(length=36), nullable=False),
        sa.Column("remote_ip", sa.String(length=45), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tracker_id"], ["trackers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_positions_tracker_id"), "positions", ["tracker_id"])
    op.create_index(op.f("ix_positions_tracker_imei"), "positions", ["tracker_imei"])
    op.create_index(
        "ix_positions_imei_received_at", "positions", ["tracker_imei", "received_at"]
    )
    op.create_index(
        "ix_positions_tracker_id_received_at", "positions", ["tracker_id", "received_at"]
    )

    op.create_table(
        "device_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tracker_id", sa.Integer(), nullable=False),
        sa.Column("tracker_imei", sa.String(length=20), nullable=False),
        sa.Column("event_code", sa.String(length=50), nullable=False),
        sa.Column("event_category", sa.String(length=50), nullable=False),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("connection_id", sa.String(length=36), nullable=False),
        sa.Column("remote_ip", sa.String(length=45), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tracker_id"], ["trackers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_device_events_tracker_id"), "device_events", ["tracker_id"])
    op.create_index(op.f("ix_device_events_tracker_imei"), "device_events", ["tracker_imei"])
    op.create_index(
        "ix_device_events_imei_received_at",
        "device_events",
        ["tracker_imei", "received_at"],
    )
    op.create_index("ix_device_events_category", "device_events", ["event_category"])

    op.execute(
        sa.text(
            "INSERT INTO fleets (company_id, name, slug, is_active) "
            "VALUES (1, 'Default Fleet', 'default', true)"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_device_events_category", table_name="device_events")
    op.drop_index("ix_device_events_imei_received_at", table_name="device_events")
    op.drop_index(op.f("ix_device_events_tracker_imei"), table_name="device_events")
    op.drop_index(op.f("ix_device_events_tracker_id"), table_name="device_events")
    op.drop_table("device_events")

    op.drop_index("ix_positions_tracker_id_received_at", table_name="positions")
    op.drop_index("ix_positions_imei_received_at", table_name="positions")
    op.drop_index(op.f("ix_positions_tracker_imei"), table_name="positions")
    op.drop_index(op.f("ix_positions_tracker_id"), table_name="positions")
    op.drop_table("positions")

    op.drop_index(op.f("ix_vehicles_fleet_id"), table_name="vehicles")
    op.drop_constraint("fk_vehicles_fleet_id", "vehicles", type_="foreignkey")
    op.drop_column("vehicles", "fleet_id")

    op.drop_index(op.f("ix_fleets_company_id"), table_name="fleets")
    op.drop_table("fleets")
