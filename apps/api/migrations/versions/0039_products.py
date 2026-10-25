"""Canonical product catalog per client.

Revision ID: 0039_products
Revises: 0038_ideal_customer_profile
"""

from alembic import op
import sqlalchemy as sa


revision = "0039_products"
down_revision = "0038_ideal_customer_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("price", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default=""),
        sa.Column("availability", sa.String(length=20), nullable=False, server_default="in_stock"),
        sa.Column("image_url", sa.String(length=600), nullable=False, server_default=""),
        sa.Column("url", sa.String(length=600), nullable=False, server_default=""),
        sa.Column("gtin", sa.String(length=20), nullable=True),
        sa.Column("brand", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("category", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="file"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="valid"),
        sa.Column("messages", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("raw", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("client_id", "sku", name="uq_products_client_sku"),
    )
    op.create_index("ix_products_agency_id", "products", ["agency_id"])
    op.create_index("ix_products_client_id", "products", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_products_client_id", table_name="products")
    op.drop_index("ix_products_agency_id", table_name="products")
    op.drop_table("products")
