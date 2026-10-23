"""add persistent API client usage counters

Revision ID: 8f914d5a2c11
Revises: cc9d84a31f27
Create Date: 2026-10-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f914d5a2c11"
down_revision: Union[str, Sequence[str], None] = "cc9d84a31f27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_client_usage",
        sa.Column("client_key", sa.String(length=64), nullable=False),
        sa.Column("minute_bucket", sa.DateTime(timezone=True), nullable=False),
        sa.Column("minute_request_count", sa.Integer(), nullable=False),
        sa.Column("daily_bucket", sa.Date(), nullable=False),
        sa.Column("daily_analysis_count", sa.Integer(), nullable=False),
        sa.Column("daily_submission_count", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("client_key"),
    )


def downgrade() -> None:
    op.drop_table("api_client_usage")
