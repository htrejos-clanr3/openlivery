"""Add image_prompt and image_error to carousel slides.

Revision ID: 0026_carousel_slide_image_prompt
Revises: 0025_carousel_generating_at
"""

from alembic import op
import sqlalchemy as sa


revision = "0026_carousel_slide_image_prompt"
down_revision = "0025_carousel_generating_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("carousel_slides", sa.Column("image_prompt", sa.Text(), nullable=True))
    op.add_column("carousel_slides", sa.Column("image_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("carousel_slides", "image_error")
    op.drop_column("carousel_slides", "image_prompt")
