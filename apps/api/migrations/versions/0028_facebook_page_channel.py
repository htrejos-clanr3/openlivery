"""Per-client Facebook Page connection.

Revision ID: 0028_facebook_page_channel
Revises: 0027_slide_product_image
"""

from alembic import op
import sqlalchemy as sa


revision = "0028_facebook_page_channel"
down_revision = "0027_slide_product_image"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "facebook_page_channels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agency_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="disconnected"),
        sa.Column("page_id", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("page_name", sa.String(length=180), nullable=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_scopes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("connection_mode", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", name="uq_facebook_page_channels_client_id"),
    )
    op.create_index("ix_facebook_page_channels_agency_id", "facebook_page_channels", ["agency_id"])
    op.create_index("ix_facebook_page_channels_client_id", "facebook_page_channels", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_facebook_page_channels_client_id", table_name="facebook_page_channels")
    op.drop_index("ix_facebook_page_channels_agency_id", table_name="facebook_page_channels")
    op.drop_table("facebook_page_channels")
