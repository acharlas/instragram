"""Initial schema for Instragram core tables."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20250128_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

TIMESTAMP_DEFAULT = sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=30), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("avatar_key", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_DEFAULT,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_DEFAULT,
            nullable=False,
        ),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.create_table(
        "follows",
        sa.Column("follower_id", sa.Integer(), nullable=False),
        sa.Column("followee_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_DEFAULT,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_DEFAULT,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["followee_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["follower_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("follower_id", "followee_id"),
    )

    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("image_key", sa.String(length=255), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_DEFAULT,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_DEFAULT,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_posts_author_created_at",
        "posts",
        ["author_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_DEFAULT,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_DEFAULT,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_comments_post_created_at",
        "comments",
        ["post_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_comments_author_id", "comments", ["author_id"], unique=False)

    op.create_table(
        "likes",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_DEFAULT,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=TIMESTAMP_DEFAULT,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "post_id"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("likes")
    op.drop_index("ix_comments_author_id", table_name="comments")
    op.drop_index("ix_comments_post_created_at", table_name="comments")
    op.drop_table("comments")
    op.drop_index("ix_posts_author_created_at", table_name="posts")
    op.drop_table("posts")
    op.drop_table("follows")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
