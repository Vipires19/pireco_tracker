"""Migration — CRM domain (customers)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_crm"
down_revision: Union[str, None] = "005_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("document", sa.String(length=14), nullable=False),
        sa.Column("document_type", sa.String(length=4), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("secondary_phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("zip_code", sa.String(length=8), nullable=True),
        sa.Column("street", sa.String(length=255), nullable=True),
        sa.Column("number", sa.String(length=20), nullable=True),
        sa.Column("complement", sa.String(length=100), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customers_company_id"), "customers", ["company_id"], unique=False)
    op.create_index(op.f("ix_customers_full_name"), "customers", ["full_name"], unique=False)
    op.create_index(op.f("ix_customers_document"), "customers", ["document"], unique=False)
    op.create_index(op.f("ix_customers_phone"), "customers", ["phone"], unique=False)
    op.create_index(op.f("ix_customers_email"), "customers", ["email"], unique=False)
    op.create_index(op.f("ix_customers_city"), "customers", ["city"], unique=False)
    op.create_index(op.f("ix_customers_status"), "customers", ["status"], unique=False)

    op.create_table(
        "customer_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_customer_audit_logs_customer_id"), "customer_audit_logs", ["customer_id"], unique=False
    )
    op.create_index(op.f("ix_customer_audit_logs_user_id"), "customer_audit_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_customer_audit_logs_action"), "customer_audit_logs", ["action"], unique=False)
    op.create_index(
        op.f("ix_customer_audit_logs_created_at"), "customer_audit_logs", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_customer_audit_logs_created_at"), table_name="customer_audit_logs")
    op.drop_index(op.f("ix_customer_audit_logs_action"), table_name="customer_audit_logs")
    op.drop_index(op.f("ix_customer_audit_logs_user_id"), table_name="customer_audit_logs")
    op.drop_index(op.f("ix_customer_audit_logs_customer_id"), table_name="customer_audit_logs")
    op.drop_table("customer_audit_logs")

    op.drop_index(op.f("ix_customers_status"), table_name="customers")
    op.drop_index(op.f("ix_customers_city"), table_name="customers")
    op.drop_index(op.f("ix_customers_email"), table_name="customers")
    op.drop_index(op.f("ix_customers_phone"), table_name="customers")
    op.drop_index(op.f("ix_customers_document"), table_name="customers")
    op.drop_index(op.f("ix_customers_full_name"), table_name="customers")
    op.drop_index(op.f("ix_customers_company_id"), table_name="customers")
    op.drop_table("customers")
