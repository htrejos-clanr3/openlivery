"""Add weekly schedule window fields to carousels.

Revision ID: 0024_carousel_schedule_window
Revises: 0023_carousel_interpret_prompt
"""

from alembic import op
import sqlalchemy as sa


revision = "0024_carousel_schedule_window"
down_revision = "0023_carousel_interpret_prompt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("carousels", sa.Column("schedule_mode", sa.String(length=20), nullable=False, server_default="once"))
    op.add_column("carousels", sa.Column("schedule_weekdays", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("carousels", sa.Column("schedule_window_start", sa.String(length=5), nullable=False, server_default="08:00"))
    op.add_column("carousels", sa.Column("schedule_window_end", sa.String(length=5), nullable=False, server_default="10:00"))
    op.add_column(
        "carousels",
        sa.Column("schedule_timezone", sa.String(length=64), nullable=False, server_default="America/Bogota"),
    )


def downgrade() -> None:
    op.drop_column("carousels", "schedule_timezone")
    op.drop_column("carousels", "schedule_window_end")
    op.drop_column("carousels", "schedule_window_start")
    op.drop_column("carousels", "schedule_weekdays")
    op.drop_column("carousels", "schedule_mode")
