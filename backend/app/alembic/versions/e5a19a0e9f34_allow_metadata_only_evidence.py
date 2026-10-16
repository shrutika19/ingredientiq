"""allow metadata-only evidence documents

Revision ID: e5a19a0e9f34
Revises: 390f098ec569
Create Date: 2026-10-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5a19a0e9f34"
down_revision: Union[str, Sequence[str], None] = "390f098ec569"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "evidence_documents",
        "content_hash",
        existing_type=sa.String(length=64),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "evidence_documents",
        "content_hash",
        existing_type=sa.String(length=64),
        nullable=False,
    )
