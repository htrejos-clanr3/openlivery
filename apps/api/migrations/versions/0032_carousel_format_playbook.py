"""Carousel Instagram format playbook: goal, CTA, hook structure.

Revision ID: 0032_carousel_format_playbook
Revises: 0031_lead_ops
"""

from alembic import op
import sqlalchemy as sa


revision = "0032_carousel_format_playbook"
down_revision = "0031_lead_ops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "carousels",
        sa.Column("content_goal", sa.String(length=20), nullable=False, server_default="loyalty"),
    )
    op.add_column(
        "carousels",
        sa.Column("cta_instruction", sa.String(length=180), nullable=False, server_default=""),
    )
    op.add_column(
        "carousels",
        sa.Column("hook_structure", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("carousels", "hook_structure")
    op.drop_column("carousels", "cta_instruction")
    op.drop_column("carousels", "content_goal")
