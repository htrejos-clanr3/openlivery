"""UCP add-on: connections, product eligibility, carts and audit events.

Revision ID: 0041_ucp
Revises: 0040_agency_meta_app
"""

from alembic import op
import sqlalchemy as sa


revision = "0041_ucp"
down_revision = "0040_agency_meta_app"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ucp_connections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("agency_id", sa.Uuid(), sa.ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("merchant_center_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("profile_slug", sa.String(length=64), nullable=False),
        sa.Column("api_key_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("adapter_kind", sa.String(length=20), nullable=False, server_default="portal"),
        sa.Column("store_base_url", sa.String(length=600), nullable=False, server_default=""),
        sa.Column("encrypted_store_credentials", sa.Text(), nullable=True),
        sa.Column("addendum_version", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("addendum_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("client_id", name="uq_ucp_connections_client"),
        sa.UniqueConstraint("profile_slug", name="uq_ucp_connections_profile_slug"),
    )
    op.create_index("ix_ucp_connections_agency_id", "ucp_connections", ["agency_id"])
    op.create_index("ix_ucp_connections_client_id", "ucp_connections", ["client_id"])
    op.create_index("ix_ucp_connections_profile_slug", "ucp_connections", ["profile_slug"])

    op.create_table(
        "ucp_products",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "connection_id",
            sa.Uuid(),
            sa.ForeignKey("ucp_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("merchant_item_id", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("checkout_eligibility", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notice_type", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("notice_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("publish_status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("last_error", sa.Text(), nullable=False, server_default=""),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("product_id", name="uq_ucp_products_product"),
    )
    op.create_index("ix_ucp_products_connection_id", "ucp_products", ["connection_id"])
    op.create_index("ix_ucp_products_product_id", "ucp_products", ["product_id"])

    op.create_table(
        "ucp_cart_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "connection_id",
            sa.Uuid(),
            sa.ForeignKey("ucp_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("continue_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ucp_cart_sessions_connection_id", "ucp_cart_sessions", ["connection_id"])

    op.create_table(
        "ucp_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "connection_id",
            sa.Uuid(),
            sa.ForeignKey("ucp_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ucp_events_connection_id", "ucp_events", ["connection_id"])


def downgrade() -> None:
    op.drop_table("ucp_events")
    op.drop_table("ucp_cart_sessions")
    op.drop_table("ucp_products")
    op.drop_table("ucp_connections")
