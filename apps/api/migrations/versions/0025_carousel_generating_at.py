"""Track in-flight carousel generation per client.

Revision ID: 0025_carousel_generating_at
Revises: 0024_carousel_schedule_window
"""

from alembic import op
import sqlalchemy as sa


revision = "0025_carousel_generating_at"
down_revision = "0024_carousel_schedule_window"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("carousels", sa.Column("generating_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("carousels", "generating_at")
