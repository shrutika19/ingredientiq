"""prevent concurrent active analyses

Revision ID: b89d64c50ed4
Revises: d1a7bc39d658
Create Date: 2026-10-15 00:13:51.472617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b89d64c50ed4'
down_revision: Union[str, Sequence[str], None] = 'd1a7bc39d658'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




def upgrade() -> None:
    op.execute("""
        CREATE UNIQUE INDEX
        uq_ingredient_analyses_active_submission
        ON ingredient_analyses (submission_id)
        WHERE status IN ('PENDING', 'PROCESSING')
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS
        uq_ingredient_analyses_active_submission
    """)
