"""Add product source image on carousel slides.

Revision ID: 0027_carousel_slide_product_image
Revises: 0026_carousel_slide_image_prompt
"""

from alembic import op
import sqlalchemy as sa


revision = "0027_slide_product_image"
down_revision = "0026_carousel_slide_image_prompt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("carousel_slides", sa.Column("product_image_data", sa.LargeBinary(), nullable=True))
    op.add_column("carousel_slides", sa.Column("product_image_mime", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("carousel_slides", "product_image_mime")
    op.drop_column("carousel_slides", "product_image_data")
