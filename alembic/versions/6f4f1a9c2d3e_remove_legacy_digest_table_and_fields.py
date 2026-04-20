"""remove legacy digest table and fields

Revision ID: 6f4f1a9c2d3e
Revises: c557f5e6e8d2
Create Date: 2026-04-18 20:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6f4f1a9c2d3e"
down_revision: Union[str, Sequence[str], None] = "c557f5e6e8d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEGACY_DIGEST_STATUS_INDEXES = (
    ("anthropic_articles", "ix_anthropic_articles_digest_status"),
    ("openai_articles", "ix_openai_articles_digest_status"),
    ("youtube_videos", "ix_youtube_videos_digest_status"),
)


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    for table_name, index_name in LEGACY_DIGEST_STATUS_INDEXES:
        if _has_index(inspector, table_name, index_name):
            op.drop_index(index_name, table_name=table_name)

    inspector = inspect(bind)
    for table_name in ("anthropic_articles", "openai_articles", "youtube_videos"):
        if _has_column(inspector, table_name, "digest_failure_reason"):
            op.drop_column(table_name, "digest_failure_reason")
        if _has_column(inspector, table_name, "digest_status"):
            op.drop_column(table_name, "digest_status")

    inspector = inspect(bind)
    if _has_table(inspector, "digests"):
        op.drop_table("digests")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    for table_name in ("anthropic_articles", "openai_articles", "youtube_videos"):
        if not _has_column(inspector, table_name, "digest_status"):
            op.add_column(
                table_name,
                sa.Column(
                    "digest_status",
                    sa.String(length=20),
                    nullable=False,
                    server_default="pending",
                ),
            )
        if not _has_column(inspector, table_name, "digest_failure_reason"):
            op.add_column(
                table_name,
                sa.Column("digest_failure_reason", sa.String(length=100), nullable=True),
            )

    inspector = inspect(bind)
    for table_name, index_name in LEGACY_DIGEST_STATUS_INDEXES:
        if not _has_index(inspector, table_name, index_name):
            op.create_index(index_name, table_name, ["digest_status"], unique=False)

    inspector = inspect(bind)
    if not _has_table(inspector, "digests"):
        op.create_table(
            "digests",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("article_type", sa.String(), nullable=False),
            sa.Column("article_id", sa.String(), nullable=False),
            sa.Column("url", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )
