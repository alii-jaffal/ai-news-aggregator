"""add story tables

Revision ID: 9bbfe748567a
Revises: 3ef7b5997f2a
Create Date: 2026-04-14 13:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9bbfe748567a"
down_revision: Union[str, Sequence[str], None] = "3ef7b5997f2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "stories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("representative_source_type", sa.String(length=20), nullable=False),
        sa.Column("representative_source_id", sa.String(), nullable=False),
        sa.Column("representative_published_at", sa.DateTime(), nullable=False),
        sa.Column("source_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("cluster_version", sa.String(length=50), nullable=False),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("window_end", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "story_source_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("story_id", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.Column("similarity_to_primary", sa.Float(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_type", "source_id", name="uq_story_source_links_source_ref"),
        sa.UniqueConstraint(
            "story_id",
            "source_type",
            "source_id",
            name="uq_story_source_links_story_source_ref",
        ),
    )
    op.create_index(
        "ix_story_source_links_story_id",
        "story_source_links",
        ["story_id"],
        unique=False,
    )
    op.create_index(
        "ix_story_source_links_published_at",
        "story_source_links",
        ["published_at"],
        unique=False,
    )
    op.create_index(
        "ix_story_source_links_is_primary",
        "story_source_links",
        ["is_primary"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_story_source_links_is_primary", table_name="story_source_links")
    op.drop_index("ix_story_source_links_published_at", table_name="story_source_links")
    op.drop_index("ix_story_source_links_story_id", table_name="story_source_links")
    op.drop_table("story_source_links")
    op.drop_table("stories")
