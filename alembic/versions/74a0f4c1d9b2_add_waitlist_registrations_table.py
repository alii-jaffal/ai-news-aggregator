"""add waitlist registrations table

Revision ID: 74a0f4c1d9b2
Revises: 4c9f2d7e1b6a
Create Date: 2026-08-06 18:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "74a0f4c1d9b2"
down_revision: Union[str, Sequence[str], None] = "4c9f2d7e1b6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "waitlist_registrations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(
        "ix_waitlist_registrations_email",
        "waitlist_registrations",
        ["email"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_waitlist_registrations_email", table_name="waitlist_registrations")
    op.drop_table("waitlist_registrations")
