"""add pipeline stage runs and worker heartbeats

Revision ID: 8d4e2f91c6ab
Revises: f19c3e7b8d42
Create Date: 2026-06-09 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8d4e2f91c6ab"
down_revision: Union[str, Sequence[str], None] = "f19c3e7b8d42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipeline_runs",
        sa.Column(
            "run_type",
            sa.String(length=30),
            nullable=False,
            server_default="full_pipeline",
        ),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column("requested_stage", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column(
            "queued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute("UPDATE pipeline_runs SET queued_at = started_at WHERE started_at IS NOT NULL")
    op.alter_column("pipeline_runs", "started_at", existing_type=sa.DateTime(timezone=True), nullable=True)
    op.create_index("ix_pipeline_runs_queued_at", "pipeline_runs", ["queued_at"], unique=False)
    op.create_index("ix_pipeline_runs_run_type", "pipeline_runs", ["run_type"], unique=False)

    op.create_table(
        "pipeline_stage_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("pipeline_run_id", sa.String(), nullable=False),
        sa.Column("stage_name", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_of_stage_run_id", sa.String(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["retry_of_stage_run_id"],
            ["pipeline_stage_runs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pipeline_stage_runs_pipeline_run_id",
        "pipeline_stage_runs",
        ["pipeline_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_stage_runs_retry_of_stage_run_id",
        "pipeline_stage_runs",
        ["retry_of_stage_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_stage_runs_stage_name",
        "pipeline_stage_runs",
        ["stage_name"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_stage_runs_status",
        "pipeline_stage_runs",
        ["status"],
        unique=False,
    )

    op.create_table(
        "worker_heartbeats",
        sa.Column("worker_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("current_run_id", sa.String(), nullable=True),
        sa.Column("current_stage_name", sa.String(length=50), nullable=True),
        sa.Column(
            "last_heartbeat_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["current_run_id"], ["pipeline_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("worker_name"),
    )
    op.create_index(
        "ix_worker_heartbeats_current_run_id",
        "worker_heartbeats",
        ["current_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_worker_heartbeats_status",
        "worker_heartbeats",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_worker_heartbeats_status", table_name="worker_heartbeats")
    op.drop_index("ix_worker_heartbeats_current_run_id", table_name="worker_heartbeats")
    op.drop_table("worker_heartbeats")

    op.drop_index("ix_pipeline_stage_runs_status", table_name="pipeline_stage_runs")
    op.drop_index("ix_pipeline_stage_runs_stage_name", table_name="pipeline_stage_runs")
    op.drop_index("ix_pipeline_stage_runs_retry_of_stage_run_id", table_name="pipeline_stage_runs")
    op.drop_index("ix_pipeline_stage_runs_pipeline_run_id", table_name="pipeline_stage_runs")
    op.drop_table("pipeline_stage_runs")

    op.drop_index("ix_pipeline_runs_run_type", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_queued_at", table_name="pipeline_runs")
    op.alter_column("pipeline_runs", "started_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    op.drop_column("pipeline_runs", "queued_at")
    op.drop_column("pipeline_runs", "requested_stage")
    op.drop_column("pipeline_runs", "run_type")
