"""Add interpret_prompt flag to carousels.

Revision ID: 0023_carousel_interpret_prompt
Revises: 0022_meta_devtools_mcp
"""

from alembic import op
import sqlalchemy as sa


revision = "0023_carousel_interpret_prompt"
down_revision = "0022_meta_devtools_mcp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "carousels",
        sa.Column("interpret_prompt", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("carousels", "interpret_prompt")
