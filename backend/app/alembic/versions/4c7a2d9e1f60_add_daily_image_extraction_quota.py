"""add daily image extraction quota

Revision ID: 4c7a2d9e1f60
Revises: 8f914d5a2c11
Create Date: 2026-10-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4c7a2d9e1f60"
down_revision: Union[str, Sequence[str], None] = "8f914d5a2c11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "api_client_usage",
        sa.Column(
            "daily_image_extraction_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("api_client_usage", "daily_image_extraction_count")
