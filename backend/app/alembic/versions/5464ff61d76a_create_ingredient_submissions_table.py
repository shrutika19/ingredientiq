"""create ingredient submissions table

Revision ID: 5464ff61d76a
Revises: 7f1782d10882
Create Date: 2026-10-14 19:53:54.928459

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5464ff61d76a'
down_revision: Union[str, Sequence[str], None] = '7f1782d10882'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ingredient_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ingredient_submissions")
