"""Migration — CustomerUser portal fields (must_change_password, last_login_at)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_customer_user_portal"
down_revision: Union[str, None] = "013_customer_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customer_users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "customer_users",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("customer_users", "last_login_at")
    op.drop_column("customer_users", "must_change_password")
