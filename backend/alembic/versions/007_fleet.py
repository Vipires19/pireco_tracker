"""Migration — Fleet domain (vehicles ERP schema)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_fleet"
down_revision: Union[str, None] = "006_crm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("customer_id", sa.Integer(), nullable=True))
    op.add_column("vehicles", sa.Column("nickname", sa.String(length=100), nullable=True))
    op.add_column("vehicles", sa.Column("brand", sa.String(length=100), nullable=True))
    op.add_column("vehicles", sa.Column("model", sa.String(length=100), nullable=True))
    op.add_column("vehicles", sa.Column("version", sa.String(length=100), nullable=True))
    op.add_column("vehicles", sa.Column("year_model", sa.Integer(), nullable=True))
    op.add_column("vehicles", sa.Column("year_manufacture", sa.Integer(), nullable=True))
    op.add_column("vehicles", sa.Column("color", sa.String(length=50), nullable=True))
    op.add_column("vehicles", sa.Column("fuel", sa.String(length=20), nullable=True))
    op.add_column("vehicles", sa.Column("renavam", sa.String(length=11), nullable=True))
    op.add_column("vehicles", sa.Column("chassis", sa.String(length=17), nullable=True))
    op.add_column("vehicles", sa.Column("category", sa.String(length=20), nullable=True))
    op.add_column("vehicles", sa.Column("cover_image", sa.String(length=512), nullable=True))
    op.add_column("vehicles", sa.Column("odometer", sa.Integer(), nullable=True))
    op.add_column("vehicles", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "vehicles",
        sa.Column("status", sa.String(length=30), nullable=True, server_default="ACTIVE"),
    )
    op.add_column("vehicles", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        sa.text(
            "UPDATE vehicles SET nickname = label WHERE nickname IS NULL AND label IS NOT NULL"
        )
    )
    op.execute(
        sa.text(
            "UPDATE vehicles SET status = CASE WHEN is_active THEN 'ACTIVE' ELSE 'INACTIVE' END "
            "WHERE status IS NULL"
        )
    )

    op.execute(
        sa.text(
            "INSERT INTO customers (full_name, document, document_type, phone, status) "
            "SELECT 'Cliente Migração — Veículos Legados', '00000000000', 'CPF', '00000000000', 'INACTIVE' "
            "WHERE EXISTS (SELECT 1 FROM vehicles WHERE customer_id IS NULL) "
            "AND NOT EXISTS (SELECT 1 FROM customers WHERE document = '00000000000')"
        )
    )
    op.execute(
        sa.text(
            "UPDATE vehicles SET customer_id = ("
            "  SELECT id FROM customers WHERE document = '00000000000' ORDER BY id LIMIT 1"
            ") WHERE customer_id IS NULL"
        )
    )

    op.drop_index(op.f("ix_vehicles_fleet_id"), table_name="vehicles")
    op.drop_constraint("fk_vehicles_fleet_id", "vehicles", type_="foreignkey")
    op.drop_column("vehicles", "fleet_id")
    op.drop_index(op.f("ix_vehicles_company_id"), table_name="vehicles")
    op.drop_constraint("vehicles_company_id_fkey", "vehicles", type_="foreignkey")
    op.drop_column("vehicles", "company_id")
    op.drop_column("vehicles", "label")
    op.drop_column("vehicles", "is_active")

    op.alter_column("vehicles", "customer_id", nullable=False)
    op.alter_column("vehicles", "status", nullable=False, server_default="ACTIVE")
    op.alter_column("vehicles", "plate", type_=sa.String(length=10), existing_type=sa.String(length=20))

    op.create_foreign_key(
        "fk_vehicles_customer_id",
        "vehicles",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_vehicles_customer_id"), "vehicles", ["customer_id"], unique=False)
    op.create_index(op.f("ix_vehicles_renavam"), "vehicles", ["renavam"], unique=False)
    op.create_index(op.f("ix_vehicles_chassis"), "vehicles", ["chassis"], unique=False)
    op.create_index(op.f("ix_vehicles_category"), "vehicles", ["category"], unique=False)
    op.create_index(op.f("ix_vehicles_status"), "vehicles", ["status"], unique=False)

    op.create_table(
        "vehicle_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vehicle_id", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vehicle_audit_logs_vehicle_id"), "vehicle_audit_logs", ["vehicle_id"], unique=False
    )
    op.create_index(
        op.f("ix_vehicle_audit_logs_user_id"), "vehicle_audit_logs", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_vehicle_audit_logs_action"), "vehicle_audit_logs", ["action"], unique=False
    )
    op.create_index(
        op.f("ix_vehicle_audit_logs_created_at"),
        "vehicle_audit_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_vehicle_audit_logs_created_at"), table_name="vehicle_audit_logs")
    op.drop_index(op.f("ix_vehicle_audit_logs_action"), table_name="vehicle_audit_logs")
    op.drop_index(op.f("ix_vehicle_audit_logs_user_id"), table_name="vehicle_audit_logs")
    op.drop_index(op.f("ix_vehicle_audit_logs_vehicle_id"), table_name="vehicle_audit_logs")
    op.drop_table("vehicle_audit_logs")

    op.drop_index(op.f("ix_vehicles_status"), table_name="vehicles")
    op.drop_index(op.f("ix_vehicles_category"), table_name="vehicles")
    op.drop_index(op.f("ix_vehicles_chassis"), table_name="vehicles")
    op.drop_index(op.f("ix_vehicles_renavam"), table_name="vehicles")
    op.drop_index(op.f("ix_vehicles_customer_id"), table_name="vehicles")
    op.drop_constraint("fk_vehicles_customer_id", "vehicles", type_="foreignkey")

    op.add_column(
        "vehicles",
        sa.Column("company_id", sa.Integer(), nullable=True, server_default="1"),
    )
    op.add_column("vehicles", sa.Column("fleet_id", sa.Integer(), nullable=True))
    op.add_column("vehicles", sa.Column("label", sa.String(length=100), nullable=True))
    op.add_column(
        "vehicles",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.execute(sa.text("UPDATE vehicles SET label = nickname WHERE label IS NULL"))
    op.execute(
        sa.text(
            "UPDATE vehicles SET is_active = CASE WHEN status = 'ACTIVE' THEN true ELSE false END"
        )
    )
    op.execute(sa.text("UPDATE vehicles SET company_id = 1 WHERE company_id IS NULL"))

    op.alter_column("vehicles", "company_id", nullable=False)
    op.alter_column("vehicles", "plate", type_=sa.String(length=20), existing_type=sa.String(length=10))

    op.create_foreign_key("vehicles_company_id_fkey", "vehicles", "companies", ["company_id"], ["id"])
    op.create_index(op.f("ix_vehicles_company_id"), "vehicles", ["company_id"], unique=False)
    op.create_foreign_key("fk_vehicles_fleet_id", "vehicles", "fleets", ["fleet_id"], ["id"])
    op.create_index(op.f("ix_vehicles_fleet_id"), "vehicles", ["fleet_id"], unique=False)

    op.drop_column("vehicles", "deleted_at")
    op.drop_column("vehicles", "status")
    op.drop_column("vehicles", "notes")
    op.drop_column("vehicles", "odometer")
    op.drop_column("vehicles", "cover_image")
    op.drop_column("vehicles", "category")
    op.drop_column("vehicles", "chassis")
    op.drop_column("vehicles", "renavam")
    op.drop_column("vehicles", "fuel")
    op.drop_column("vehicles", "color")
    op.drop_column("vehicles", "year_manufacture")
    op.drop_column("vehicles", "year_model")
    op.drop_column("vehicles", "version")
    op.drop_column("vehicles", "model")
    op.drop_column("vehicles", "brand")
    op.drop_column("vehicles", "nickname")
    op.drop_column("vehicles", "customer_id")
