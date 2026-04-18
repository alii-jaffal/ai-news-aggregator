"""add story digests and story digest status fields

Revision ID: c557f5e6e8d2
Revises: 9bbfe748567a
Create Date: 2026-04-17 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c557f5e6e8d2"
down_revision: Union[str, Sequence[str], None] = "9bbfe748567a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stories",
        sa.Column(
            "story_digest_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "stories",
        sa.Column("story_digest_failure_reason", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "stories",
        sa.Column("story_digest_input_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "stories",
        sa.Column("story_digest_last_processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_stories_story_digest_status",
        "stories",
        ["story_digest_status"],
        unique=False,
    )

    op.create_table(
        "story_digests",
        sa.Column("story_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("why_it_matters", sa.Text(), nullable=False),
        sa.Column("disagreement_notes", sa.Text(), nullable=True),
        sa.Column("synthesis_mode", sa.String(length=30), nullable=False),
        sa.Column("available_source_count", sa.Integer(), nullable=False),
        sa.Column("used_source_count", sa.Integer(), nullable=False),
        sa.Column("generated_input_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("story_id"),
    )

    op.execute("UPDATE stories SET story_digest_status = 'pending'")


def downgrade() -> None:
    op.drop_table("story_digests")
    op.drop_index("ix_stories_story_digest_status", table_name="stories")
    op.drop_column("stories", "story_digest_last_processed_at")
    op.drop_column("stories", "story_digest_input_hash")
    op.drop_column("stories", "story_digest_failure_reason")
    op.drop_column("stories", "story_digest_status")
