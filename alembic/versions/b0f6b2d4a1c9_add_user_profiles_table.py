"""add user profiles table

Revision ID: b0f6b2d4a1c9
Revises: 6f4f1a9c2d3e
Create Date: 2026-04-22 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b0f6b2d4a1c9"
down_revision: Union[str, Sequence[str], None] = "6f4f1a9c2d3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("background", sa.Text(), nullable=False),
        sa.Column("expertise_level", sa.String(length=50), nullable=False),
        sa.Column("interests", sa.JSON(), nullable=False),
        sa.Column("preferred_source_types", sa.JSON(), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column(
            "newsletter_top_n",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_user_profiles_is_active", "user_profiles", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_profiles_is_active", table_name="user_profiles")
    op.drop_table("user_profiles")
