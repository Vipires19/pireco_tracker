"""Migration — Customer users (Portal do Cliente base)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_customer_users"
down_revision: Union[str, None] = "012_device_telemetry_sync"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="ACTIVE"),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="VIEWER"),
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
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_users_customer_id", "customer_users", ["customer_id"])
    op.create_index("ix_customer_users_email", "customer_users", ["email"], unique=True)
    op.create_index("ix_customer_users_status", "customer_users", ["status"])


def downgrade() -> None:
    op.drop_index("ix_customer_users_status", table_name="customer_users")
    op.drop_index("ix_customer_users_email", table_name="customer_users")
    op.drop_index("ix_customer_users_customer_id", table_name="customer_users")
    op.drop_table("customer_users")
