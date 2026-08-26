"""Link approved carousels to Instagram content_items / publications.

Revision ID: 0021_carousel_instagram_bridge
Revises: 0020_instagram_publishing
"""

from alembic import op
import sqlalchemy as sa


revision = "0021_carousel_instagram_bridge"
down_revision = "0020_instagram_publishing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("carousels", sa.Column("content_item_id", sa.Uuid(), nullable=True))
    op.add_column("carousels", sa.Column("publication_id", sa.Uuid(), nullable=True))
    op.create_index("ix_carousels_content_item_id", "carousels", ["content_item_id"])
    op.create_index("ix_carousels_publication_id", "carousels", ["publication_id"])
    op.create_foreign_key(
        "fk_carousels_content_item_id",
        "carousels",
        "content_items",
        ["content_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_carousels_publication_id",
        "carousels",
        "publications",
        ["publication_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_carousels_publication_id", "carousels", type_="foreignkey")
    op.drop_constraint("fk_carousels_content_item_id", "carousels", type_="foreignkey")
    op.drop_index("ix_carousels_publication_id", table_name="carousels")
    op.drop_index("ix_carousels_content_item_id", table_name="carousels")
    op.drop_column("carousels", "publication_id")
    op.drop_column("carousels", "content_item_id")
