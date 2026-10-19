"""add analysis evidence snapshots

Revision ID: cc9d84a31f27
Revises: e5a19a0e9f34
Create Date: 2026-10-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "cc9d84a31f27"
down_revision: Union[str, Sequence[str], None] = "d73e981c1f3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ingredient_analyses",
        sa.Column(
            "evidence_references",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "ingredient_analyses",
        sa.Column(
            "evidence_coverage",
            sa.String(length=20),
            server_default="unavailable",
            nullable=False,
        ),
    )
    op.add_column(
        "ingredient_analyses",
        sa.Column(
            "retrieval_config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_analysis_evidence_coverage",
        "ingredient_analyses",
        "evidence_coverage IN ('full', 'partial', 'unavailable')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_analysis_evidence_coverage",
        "ingredient_analyses",
        type_="check",
    )
    op.drop_column("ingredient_analyses", "retrieval_config")
    op.drop_column("ingredient_analyses", "evidence_coverage")
    op.drop_column("ingredient_analyses", "evidence_references")
