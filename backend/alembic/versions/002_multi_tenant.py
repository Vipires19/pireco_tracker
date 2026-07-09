"""Multi-tenant schema — Company, Vehicle, Tracker, TrackerAssignment."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_multi_tenant"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_devices_imei", table_name="devices")
    op.drop_table("devices")

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_companies_slug"), "companies", ["slug"], unique=True)

    op.create_table(
        "vehicles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("plate", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vehicles_company_id"), "vehicles", ["company_id"])
    op.create_index(op.f("ix_vehicles_plate"), "vehicles", ["plate"])

    op.create_table(
        "trackers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("imei", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_remote_ip", sa.String(length=45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trackers_company_id"), "trackers", ["company_id"])
    op.create_index(op.f("ix_trackers_imei"), "trackers", ["imei"], unique=True)

    op.create_table(
        "tracker_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tracker_id", sa.Integer(), nullable=False),
        sa.Column("vehicle_id", sa.Integer(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("unassigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["tracker_id"], ["trackers.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tracker_assignments_tracker_id"), "tracker_assignments", ["tracker_id"]
    )
    op.create_index(
        op.f("ix_tracker_assignments_vehicle_id"), "tracker_assignments", ["vehicle_id"]
    )

    op.execute(
        sa.text(
            "INSERT INTO companies (name, slug, is_active) "
            "VALUES ('Default Company', 'default', true)"
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tracker_assignments_vehicle_id"), table_name="tracker_assignments")
    op.drop_index(op.f("ix_tracker_assignments_tracker_id"), table_name="tracker_assignments")
    op.drop_table("tracker_assignments")
    op.drop_index(op.f("ix_trackers_imei"), table_name="trackers")
    op.drop_index(op.f("ix_trackers_company_id"), table_name="trackers")
    op.drop_table("trackers")
    op.drop_index(op.f("ix_vehicles_plate"), table_name="vehicles")
    op.drop_index(op.f("ix_vehicles_company_id"), table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_index(op.f("ix_companies_slug"), table_name="companies")
    op.drop_table("companies")

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("imei", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_devices_imei"), "devices", ["imei"], unique=True)
