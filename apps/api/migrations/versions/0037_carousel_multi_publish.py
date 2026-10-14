"""Carousel multi-network publish results (Instagram + LinkedIn POC).

Revision ID: 0037_carousel_multi_publish
Revises: 0036_legal_acceptances
"""

from alembic import op
import sqlalchemy as sa


revision = "0037_carousel_multi_publish"
down_revision = "0036_legal_acceptances"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "carousels",
        sa.Column("linkedin_post_id", sa.String(length=300), nullable=True),
    )
    op.add_column(
        "carousels",
        sa.Column("publish_results", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )


def downgrade() -> None:
    op.drop_column("carousels", "publish_results")
    op.drop_column("carousels", "linkedin_post_id")
