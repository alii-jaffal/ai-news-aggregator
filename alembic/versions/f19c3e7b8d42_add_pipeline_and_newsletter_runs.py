"""add pipeline and newsletter runs

Revision ID: f19c3e7b8d42
Revises: b0f6b2d4a1c9
Create Date: 2026-04-27 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f19c3e7b8d42"
down_revision: Union[str, Sequence[str], None] = "b0f6b2d4a1c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("trigger_source", sa.String(length=20), nullable=False),
        sa.Column("requested_hours", sa.Integer(), nullable=False),
        sa.Column("requested_top_n", sa.Integer(), nullable=True),
        sa.Column("profile_slug", sa.String(length=100), nullable=False),
        sa.Column(
            "send_email",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("scraping_summary", sa.JSON(), nullable=True),
        sa.Column("processing_summary", sa.JSON(), nullable=True),
        sa.Column("digest_summary", sa.JSON(), nullable=True),
        sa.Column("email_summary", sa.JSON(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_runs_profile_slug", "pipeline_runs", ["profile_slug"], unique=False)
    op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"], unique=False)
    op.create_index(
        "ix_pipeline_runs_trigger_source",
        "pipeline_runs",
        ["trigger_source"],
        unique=False,
    )

    op.create_table(
        "newsletter_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("pipeline_run_id", sa.String(), nullable=True),
        sa.Column("profile_slug", sa.String(length=100), nullable=False),
        sa.Column("window_hours", sa.Integer(), nullable=False),
        sa.Column("resolved_top_n", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("greeting", sa.Text(), nullable=False),
        sa.Column("introduction", sa.Text(), nullable=False),
        sa.Column(
            "sent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("article_count", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_newsletter_runs_created_at",
        "newsletter_runs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_newsletter_runs_pipeline_run_id",
        "newsletter_runs",
        ["pipeline_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_newsletter_runs_profile_slug",
        "newsletter_runs",
        ["profile_slug"],
        unique=False,
    )
    op.create_index("ix_newsletter_runs_sent", "newsletter_runs", ["sent"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_newsletter_runs_sent", table_name="newsletter_runs")
    op.drop_index("ix_newsletter_runs_profile_slug", table_name="newsletter_runs")
    op.drop_index("ix_newsletter_runs_pipeline_run_id", table_name="newsletter_runs")
    op.drop_index("ix_newsletter_runs_created_at", table_name="newsletter_runs")
    op.drop_table("newsletter_runs")

    op.drop_index("ix_pipeline_runs_trigger_source", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_status", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_profile_slug", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
