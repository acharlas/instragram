"""Add index on follows.followee_id for feed queries."""

from collections.abc import Sequence

from alembic import op

revision: str = "20250128_0002"
down_revision: str | None = "20250128_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_follows_followee_id",
        "follows",
        ["followee_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_follows_followee_id", table_name="follows")
