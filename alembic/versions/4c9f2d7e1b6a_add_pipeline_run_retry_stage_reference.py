"""add pipeline run retry stage reference

Revision ID: 4c9f2d7e1b6a
Revises: 8d4e2f91c6ab
Create Date: 2026-06-23 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c9f2d7e1b6a"
down_revision: Union[str, Sequence[str], None] = "8d4e2f91c6ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipeline_runs",
        sa.Column("retry_stage_run_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_pipeline_runs_retry_stage_run_id",
        "pipeline_runs",
        ["retry_stage_run_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_pipeline_runs_retry_stage_run_id_pipeline_stage_runs",
        "pipeline_runs",
        "pipeline_stage_runs",
        ["retry_stage_run_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_pipeline_runs_retry_stage_run_id_pipeline_stage_runs",
        "pipeline_runs",
        type_="foreignkey",
    )
    op.drop_index("ix_pipeline_runs_retry_stage_run_id", table_name="pipeline_runs")
    op.drop_column("pipeline_runs", "retry_stage_run_id")
